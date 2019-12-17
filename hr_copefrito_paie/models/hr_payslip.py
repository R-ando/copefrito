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

from dateutil import relativedelta

from openerp import models, api, fields
from openerp.netsvc import logging

_logger = logging.getLogger(__name__)

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

import datetime
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.exceptions import ValidationError
from lxml import etree
import openerp.addons.decimal_precision as dp


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    prev_state = fields.Char(string=u'Previous state')
    state = fields.Selection(selection=[
        ('draft', 'Brouillon'),
        ('verify', 'En cours'),
        ('instance', 'Instance'),
        ('validate', u'Validé'),
        ('waiting', u'En attente de déclaration'),
        ('done', u'Terminé'),
        ('cancel', u'Annulé'),
    ],
        help='* When the payslip is created the status is \'Draft\'.\
        \n* If the payslip is under verification, the status is \'Waiting\'. \
        \n* If the payslip is verified, the status is \'Validate\'. \
        \n* If the payslip is confirmed then status is set to \'Done\'.\
        \n* When user cancel payslip the status is \'Rejected\'.', default='draft')

    payment_mode = fields.Many2one('hr.payslip.payment.mode', u'Mode de paiement')
    payment_mobile = fields.Many2one('hr.payslip.payment.mobile', string=u"Mobile banking")
    bank_account_id = fields.Many2one('res.partner.bank', 'Bank Account Number', help="Employee bank salary account")
    tel_for_payment = fields.Char('Payment Phone Number')
    leave_employee = fields.One2many('hr.holidays', 'contract_id', compute='_get_holidays')
    nb_leave = fields.Float('Number of legal leaves', compute='_get_holidays')
    nb_leave_deductible = fields.Float('Number of legal leaves', compute='_get_holidays')
    struct_id = fields.Many2one('hr.payroll.structure', related='contract_id.struct_id', readonly=True,
                                string=u'Structure 2', states={'draft': [('readonly', False)]},
                                help='Defines the rules that have to be applied to this payslip, accordingly to the contract chosen. If you let empty the field contract, this field isn\'t mandatory anymore and thus the rules applied will be all the rules set on the structure of all contracts of the employee valid for the chosen period')
    service = fields.Many2one('hr.department', related='employee_id.department_id', string=u"Service")
    matricule = fields.Char(string=u"Matricule", related='employee_id.identification_cdi_id')
    num_contract = fields.Char(string=u"N° Contrat", related='contract_id.num_contract')
    button_rectify_visible = fields.Boolean(compute='button_visibility')
    button_verify_visible = fields.Boolean(compute='button_visibility')
    button_submit_visible = fields.Boolean(compute='button_visibility')
    button_compute_visible = fields.Boolean(compute='button_visibility')
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', u'Entrées', required=False, readonly=True,
                                     states={'draft': [('readonly', False)], 'verify': [('readonly', False)],
                                             'instance': [('readonly', False)], 'validate': [('readonly', False)]})
    active = fields.Boolean(string=u"Active", default=True)

    # Fields use to keep track value when computing the sheet
    monthly_hours_contract_info = fields.Many2one('monthly.hours.contract.data', string=u'Volume horaire mensuelle')
    taux_horaire_info = fields.Float(u"Taux horaire")
    department_id_info = fields.Many2one('hr.department', string=u'Service')
    job_id_info = fields.Many2one('hr.job', string=u"Poste")
    taux_cnaps_info = fields.Float(u"Taux CNaPs employé")
    taux_cnaps_patron_info = fields.Float(u"Taux CNaPS Patronale")
    org_sante_id_info = fields.Many2one("res.organisme.medical", string=u"Organisme Médical")
    taux_om_emp_info = fields.Float(u"Taux OM employé")
    taux_om_patr_info = fields.Float("Taux OM patronale")
    work_amount_info = fields.Float(u"Nbr. Heures Travaillées")
    is_stc = fields.Boolean("STC")
    payslip_link_id = fields.Many2one('hr.payslip', string=u"Bulletin lié")
    around_value = fields.Integer(string=u"Valeur arrondie", compute='compute_around_value', store=True)
    ttl_slry = fields.Float(u"salaire total", compute='get_total_salary')

    signature = fields.Binary("signature", compute='get_signature', store=False, track_visibility='onchange')

    payment_date = fields.Date(u"Date de paiement", compute='get_payment_date', store=False)
    seq = fields.Integer(string=u'Sequence')
    total_amount = fields.Float(string="Montant total", compute='get_total_amount',
                                digits=dp.get_precision('Montant général'), store=True)

    computed_payslip = fields.Boolean(string='Already computed payslip', default=False)
    non_taxable_amount = fields.Float(string='Non Taxable Amount', digits=dp.get_precision('Montant général'))

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO GET TIMESHEET FOR THE DEFINED PERIOD AND TO FILL AUTOMATICALLY
                   INPUTS FROM TIMESHEET DATA
    @Author: Sylvain Michel R.
    @Begins on : 16/01/2017
    @Latest update on : 16/01/2017
    __________________________________________________________________________________________

    """

    @api.one
    @api.depends('input_line_ids.amount')
    def get_total_amount(self):
        line_ids = self.input_line_ids.mapped('amount')
        self.total_amount = sum(line_ids)
        self.computed_payslip = False

    @api.one
    def get_validator(self):
        payslip_run_obj = self.env['hr.payslip.run']
        domain = [('date_start', '=', self.date_from), ('company_id', '=', self.company_id.id)]
        payslip_run_id = payslip_run_obj.search(domain, limit=1)
        validator = payslip_run_id.responsable
        return validator

    @api.one
    def get_payment_date(self):
        payslip_run_obj = self.env['hr.payslip.run']
        domain = [('date_start', '=', self.date_from), ('company_id', '=', self.company_id.id)]
        payslip_run_id = payslip_run_obj.search(domain, limit=1)
        self.payment_date = payslip_run_id.date_payement
        if self.payment_date:
            payment_date = (datetime.strptime(str(payslip_run_id.date_payement), "%Y-%m-%d")).strftime('%d/%m/%Y')
            return payment_date

    @api.one
    def get_signature(self):
        self.signature = self.payslip_run_id.responsable.signature_img

    @api.multi
    def get_total_salary(self):
        total = 0
        for rubric in self.input_line_ids:
            if rubric.line_ids.rubric_id.paylip_rubric_conf_id.mouvement == '+':
                total = total + rubric.input_line_ids.amount2 * rubric.input_line_ids.quantity
            return total

    def get_inputs(self, cr, uid, contract_ids, date_from, date_to, context=None):
        res = []
        contract_obj = self.pool.get('hr.contract')
        rule_obj = self.pool.get('hr.salary.rule')

        structure_ids = contract_obj.get_all_structures(cr, uid, contract_ids, context=context)
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        contract_ids_recs = contract_obj.browse(cr, uid, contract_ids, context=context)
        # variable_rubric_ids = contract_ids_recs.variable_rubric_ids.mapped('rule_info_id').ids
        rubric_fixe = contract_ids_recs.rubric_ids.filtered(lambda r: r.rubric_conf.type == 'fixe')
        variable_rubric_ids = contract_ids_recs.variable_rubric_ids.mapped('rule_info_id').ids + [
            self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid,
                                                           'hr_copefrito_paie.hr_rule_SBA')] + rubric_fixe.mapped(
            'rubric_conf.rule_info_id').ids
        sorted_rule_ids = list(set(sorted_rule_ids) & set(variable_rubric_ids))

        sequence_index = 0

        for contract in contract_obj.browse(cr, uid, contract_ids, context=context):
            for rule in rule_obj.browse(cr, uid, sorted_rule_ids, context=context):
                if rule.input_ids:
                    for input in rule.input_ids:
                        sequence_index += 1
                        amount = 0.0

                        if rule.rubric_id and contract.rubric_ids.filtered(lambda r: r.rubric_conf == rule.rubric_id):
                            rubric = contract.rubric_ids.filtered(lambda r: r.rubric_conf == rule.rubric_id)
                            amount = rubric.montant

                        inputs = {
                            'name': input.name,
                            'code': input.code,
                            'amount': amount,
                            'sequence': sequence_index,
                            'contract_id': contract.id,
                            'rule_id': rule.id,
                            'quantity': 0.0
                        }

                        if rule.rubric_id:
                            inputs['product_uom'] = rule.rubric_id.product_uom.id

                        is_input = True
                        # if input.code == 'INFO_100' and contract.status != 'journalier': continue
                        # if input.code == 'INFO_100':

                        if contract.status == 'journalier' and input.code == 'INFO_100':
                            res += [inputs]
                        elif rule.rubric_id.id in contract.rubric_ids.mapped('rubric_conf.id'):
                            is_incomplete, base_amount = contract.check_incomplete_month(date_from, date_to)[0]
                            if is_incomplete:
                                inputs.update({
                                    'amount': base_amount.get(rule.rubric_id.id, 0),
                                    'amount2': base_amount.get(rule.rubric_id.id, 0)
                                })
                                res += [inputs]

                        if input.code not in ['INFO_100', 'INFO_310']:
                            if rule.rubric_id.type == 'fixe':
                                if rule.rubric_id.status == 'journalier' and contract.status != 'journalier': is_input = False
                                if rule.rubric_id.status != 'journalier': is_input = False
                            if rule.rubric_id.hr_department_ids:
                                if contract.department_id not in rule.rubric_id.hr_department_ids: is_input = False

                            if rule.rubric_id.company_ids:
                                if contract.employee_id.company_id not in rule.rubric_id.company_ids: is_input = False
                            if is_input: res += [inputs]

                        elif input.code == 'INFO_310' and contract.additional_hour:
                            res += [inputs]
        sorted_res = sorted(res, key=lambda r: r.get('code'))
        return sorted_res

    def update_inputs(self, cr, uid, ids, context=None):
        for payslip in self.browse(cr, uid, ids, context):
            res = []
            contract_obj = self.pool.get('hr.contract')
            rule_obj = self.pool.get('hr.salary.rule')
            input_obj = self.pool.get('hr.payslip.input')

            structure_ids = contract_obj.get_all_structures(cr, uid, [payslip.contract_id.id], context=context)
            rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
            sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]

            sequence_index = 0
            code_inputs_ids = [i.code_rubric for i in payslip.input_line_ids]

            run_id = payslip.payslip_run_id
            run_rubric_ids = run_id.class_ids.mapped('rubric_ids')

            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                                  'hr_rule_NT')
            info_model, info_model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                            'hr_copefrito_paie',
                                                                                            'hr_rule_NT_INFO')

            for contract in contract_obj.browse(cr, uid, [payslip.contract_id.id], context=context):
                for rule in rule_obj.browse(cr, uid, sorted_rule_ids, context=context):
                    if rule.input_ids:
                        for input in rule.input_ids:
                            sequence_index += 1
                            amount = 0.0

                            if rule.id == model_id or rule.id == info_model_id and not rule.non_taxable:
                                continue

                            if rule.rubric_id and contract.rubric_ids.filtered(
                                    lambda r: r.rubric_conf == rule.rubric_id):
                                rubric = contract.rubric_ids.filtered(lambda r: r.rubric_conf == rule.rubric_id)
                                amount = rubric.montant

                            if rule.rubric_id.code not in code_inputs_ids and rule.rubric_id.code in payslip.contract_id.variable_rubric_ids.mapped(
                                    'code'):

                                inputs = {
                                    'name': input.name,
                                    'code': input.code,
                                    'amount': amount,
                                    'sequence': sequence_index,
                                    'contract_id': contract.id,
                                    'rule_id': rule.id,
                                    'quantity': 1.0,
                                    'payslip_id': payslip.id
                                }

                                input_rubric_id = run_rubric_ids.filtered(
                                    lambda r: r.paylip_rubric_conf_id.id == rule.rubric_id.id)
                                if input_rubric_id:
                                    inputs['rubric_id'] = input_rubric_id.id
                                    if input_rubric_id.state == 'neutre':
                                        input_rubric_id.state = 'draft'

                                if rule.rubric_id:
                                    inputs['product_uom'] = rule.rubric_id.product_uom.id

                                is_input = True
                                if input.code != 'INFO_310' and input.code != 'INFO_100':
                                    if rule.rubric_id.type == 'fixe':
                                        if rule.rubric_id.status == 'journalier' and contract.status != 'journalier': is_input = False
                                        if rule.rubric_id.status != 'journalier': is_input = False
                                    if rule.rubric_id.hr_department_ids:
                                        if contract.department_id not in rule.rubric_id.hr_department_ids: is_input = False

                                    if rule.rubric_id.company_ids:
                                        if contract.employee_id.company_id not in rule.rubric_id.company_ids: is_input = False
                                    if is_input: input_obj.create(cr, uid, inputs)

                                elif input.code == 'INFO_310' and contract.additional_hour:
                                    input_obj.create(cr, uid, inputs)

                for input_id in payslip.input_line_ids:
                    if input_id.rule_id.rubric_id.id not in payslip.contract_id.variable_rubric_ids.ids and input_id.rubric_id.state not in [
                        'validate',
                        'closed'] and input_id.rule_id.rubric_id.id not in payslip.contract_id.rubric_ids.mapped(
                        'rubric_conf').ids:
                        if len(input_id.rubric_id.input_ids) == 1:
                            input_id.rubric_id.state = 'neutre'
                        input_id.unlink()

    def get_contract(self, cr, uid, employee, date_from, date_to, context=None):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the id of  the contract in state  for the given employee that need to be considered for the given dates
        """
        contract_ids = super(HrPayslip, self).get_contract(cr, uid, employee, date_from, date_to, context)

        # contract_match = self.pool.get('hr.employee').get_matched_contract(cr, uid, [employee], date_to, context)
        match_contrat = employee.get_matched_contract(date_to)

        if match_contrat:
            contract_ids += match_contrat[0]

        contract_obj = self.pool.get('hr.contract')
        if context.get('default_is_stc'):
            contract_ids = contract_obj.search(cr, uid, [('id', 'in', contract_ids), ('state', 'in', ['close'])],
                                               context=context)
        else:
            contract_ids = contract_obj.search(cr, uid, [('id', 'in', contract_ids),
                                                         ('state', 'in', ['open', 'renewed', 'active'])],
                                               context=context)

        return contract_ids

    def compute_sheet(self, cr, uid, ids, context=None):
        payslip_line_obj = self.pool.get('hr.payslip.line')
        ir_sequence_obj = self.pool.get('ir.sequence')
        payslip_rubric_obj = self.pool.get('hr.payslip.rubric')
        hr_salary_obj = self.pool.get('hr.salary.rule')
        hr_contract_obj = self.pool.get('hr.contract')

        for payslip in self.browse(cr, uid, ids, context=context):
            for input_line in payslip.input_line_ids:
                input_line.compute_amount()
            if not payslip.payslip_link_id:
                payslip.payslip_link_id = self.get_payslip_link_id(cr, uid, payslip.id, context)[0]

            number = payslip.number or ir_sequence_obj.next_by_code(cr, uid, 'salary.slip')

            # delete old payslip lines
            old_slipline_ids = payslip_line_obj.search(cr, uid, [('slip_id', '=', payslip.id)], context=context)
            if len(old_slipline_ids) > 0 and payslip.computed_payslip or len(
                    old_slipline_ids) > 0 and payslip.state not in ['draft']:
                slip_line_ids = payslip_line_obj.browse(cr, uid, old_slipline_ids)
                slip_line_ids.unlink()
                _logger.info(" ==== Deleting payslips lines successfully done %s ====" % payslip.name)

            if payslip.contract_id:
                # set the list of contract for which the am have to be applied
                contract_ids = [payslip.contract_id.id]
            else:
                # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, payslip.employee_id, payslip.date_from, payslip.date_to,
                                                 context=context)
            lines = []
            categories_dict = {}

            def _sum_salary_rule_category(localdict, category, amount):
                if category.parent_id:
                    localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
                if category.code in localdict['categories'].dict:
                    amount += localdict['categories'].dict[category.code]
                localdict['categories'].dict[category.code] = amount
                return localdict

            class BrowsableObject(object):
                def __init__(self, pool, cr, uid, employee_id, dict):
                    self.pool = pool
                    self.cr = cr
                    self.uid = uid
                    self.employee_id = employee_id
                    self.dict = dict

                def __getattr__(self, attr):
                    return attr in self.dict and self.dict.__getitem__(attr) or 0.0

            class InputLine(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(self, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = datetime.now().strftime('%Y-%m-%d')
                    self.cr.execute("SELECT sum(amount) as sum\
                                FROM hr_payslip as hp, hr_payslip_input as pi \
                                WHERE hp.employee_id = %s AND hp.state = 'done' \
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                                    (self.employee_id, from_date, to_date, code))
                    res = self.cr.fetchone()[0]
                    return res or 0.0

            class WorkedDays(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def _sum(self, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = datetime.now().strftime('%Y-%m-%d')
                    self.cr.execute("SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours\
                                FROM hr_payslip as hp, hr_payslip_worked_days as pi \
                                WHERE hp.employee_id = %s AND hp.state = 'done'\
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s",
                                    (self.employee_id, from_date, to_date, code))
                    return self.cr.fetchone()

                def sum(self, code, from_date, to_date=None):
                    res = self._sum(code, from_date, to_date)
                    return res and res[0] or 0.0

                def sum_hours(self, code, from_date, to_date=None):
                    res = self._sum(code, from_date, to_date)
                    return res and res[1] or 0.0

            class Payslips(BrowsableObject):
                """a class that will be used into the python code, mainly for usability purposes"""

                def sum(self, code, from_date, to_date=None):
                    if to_date is None:
                        to_date = datetime.now().strftime('%Y-%m-%d')
                    self.cr.execute("SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)\
                                FROM hr_payslip as hp, hr_payslip_line as pl \
                                WHERE hp.employee_id = %s AND hp.state = 'done' \
                                AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s",
                                    (self.employee_id, from_date, to_date, code))
                    res = self.cr.fetchone()
                    return res and res[0] or 0.0

            mod_obj = self.pool.get('ir.model.data')
            form_id = mod_obj.get_object_reference(cr, uid, 'hr_copefrito_paie', 'INFO_RUBR')
            non_taxable_rule_ids = hr_contract_obj.browse(cr, uid, contract_ids).struct_id.rule_ids.filtered(
                lambda x: x.non_taxable and x.category_id.id == form_id[1])

            rules = {}
            worked_days = {}

            inputs = {}
            for input_line in payslip.input_line_ids:
                inputs[input_line.code] = input_line

            categories_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, categories_dict)
            input_obj = InputLine(self.pool, cr, uid, payslip.employee_id.id, inputs)
            worked_days_obj = WorkedDays(self.pool, cr, uid, payslip.employee_id.id, worked_days)
            payslip_obj = Payslips(self.pool, cr, uid, payslip.employee_id.id, payslip)
            rules_obj = BrowsableObject(self.pool, cr, uid, payslip.employee_id.id, rules)

            baselocaldict = {'categories': categories_obj, 'rules': rules_obj, 'payslip': payslip_obj,
                             'worked_days': worked_days_obj, 'inputs': input_obj}

            localdict = dict(baselocaldict, employee=payslip.employee_id, contract=payslip.employee_id.contract_id)

            localdict['result'] = None
            localdict['result_qty'] = 1.0
            localdict['result_rate'] = 100

            payslip.non_taxable_amount = 0
            for rule in non_taxable_rule_ids:
                if hr_salary_obj.satisfy_condition(cr, uid, rule.id, localdict, context=context):
                    amount, qty, rate = hr_salary_obj.compute_rule(cr, uid, rule.id, localdict, context=context)
                    if rule.rubric_id.mouvement == '-':
                        payslip.non_taxable_amount -= amount
                    else:
                        payslip.non_taxable_amount += amount

            for line in self.pool.get('hr.payslip').get_payslip_lines(cr, uid, contract_ids, payslip.id,
                                                                      context=context):
                if payslip.contract_id.org_sante_id and line['code'] == "RET_ORGM_EMP":
                    line['name'] = payslip.contract_id.org_sante_id.name
                lines.append((0, 0, line))

            payslip.line_ids = lines
            payslip.number = number

            rubric_ids = self.pool.get('hr.payslip.rubric').search(cr, uid,
                                                                   [('payslip_run', '=', payslip.payslip_run_id.id)])

            for rubric in rubric_ids:
                rubric_id = payslip_rubric_obj.browse(cr, uid, rubric)
                payslip_line_rubric = payslip_line_obj.search(cr, uid, [('id', 'in', payslip.line_ids.ids), (
                    'salary_rule_id', '=', rubric_id.paylip_rubric_conf_id.rule_id.id)])
                if payslip_line_rubric:
                    cr.execute(""" UPDATE hr_payslip_line SET rubric_id = %s WHERE id = %s """,
                               (rubric, payslip_line_rubric[0],))
                    cr.commit()

            # update info
            if payslip.contract_id:
                contract = payslip.contract_id
                payslip.monthly_hours_contract_info = contract.monthly_hours_amount_id
                line_sme = payslip.input_line_ids.filtered(lambda l: l.code == "SME")
                payslip.taux_horaire_info = line_sme.amount2
                payslip.work_amount_info = line_sme.quantity
                payslip.department_id_info = contract.department_id
                payslip.org_sante_id_info = contract.org_sante_id
                payslip.job_id_info = contract.job_id
                payslip.taux_om_emp_info = contract.org_sante_id.taux_salarial
                payslip.taux_om_patr_info = contract.org_sante_id.taux_patronal
                # payslip.payment_mode = payslip.contract_id.payslip_payment_mode_id

                if contract.employee_id.company_id.use_parent_param is True:
                    payslip.taux_cnaps_info = contract.employee_id.company_id.parent_id.cotisation_cnaps_emp
                    payslip.taux_cnaps_patron_info = contract.employee_id.company_id.parent_id.cotisation_cnaps_patr
                else:
                    payslip.taux_cnaps_info = contract.employee_id.company_id.cotisation_cnaps_emp
                    payslip.taux_cnaps_patron_info = contract.employee_id.company_id.cotisation_cnaps_patr

            payslip.computed_payslip = True

            def redefine_sequence(ext_id, sequence, is_rub=False):
                rule_id = self.pool.get('ir.model.data').xmlid_to_res_id(cr, uid, ext_id)
                if is_rub:
                    rule_id = self.pool.get('hr.payslip.rubric.config').browse(cr, uid, [rule_id]).rule_id.id
                rule_line_id = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == rule_id)
                if rule_line_id:
                    cr.execute(""" UPDATE hr_payslip_line SET sequence = %s WHERE id = %s""",
                               (sequence, rule_line_id.id,))
                    cr.commit()

            redefine_sequence('hr_copefrito_paie.hr_payroll_rules_IRSA_DED', 745)
            redefine_sequence('hr_copefrito_paie.RUBRIC_799', 799, is_rub=True)
        return True

    @api.multi
    def write(self, vals):
        for rec in self:
            prv_st = rec.state
            if vals.get('state', False) and vals.get('state', False) != prv_st:
                vals['prev_state'] = prv_st
                # return super(HrPayslip, rec).write(vals)
        return super(HrPayslip, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(HrPayslip, self).create(vals)
        res.number = ' '
        payslip_run_id = vals.get('payslip_run_id')
        if vals.get('is_stc'):
            if not vals.get('payslip_run_id'):
                raise UserError("Il n'existe aucune période de paie dans cet intervalle de date.")
            employee_id = vals.get('employee_id')
            run_rec = self.env['hr.payslip.run'].browse(payslip_run_id)
            payslip_id = run_rec.slip_ids.filtered(lambda p: p.employee_id.id == employee_id and not p.is_stc)
            if payslip_id:
                payslip_id.cancel_sheet()
        if payslip_run_id:
            run_rec = self.env['hr.payslip.run'].browse(payslip_run_id)
            run_rec.refresh()
        return res

    @api.one
    @api.constrains('employee_id', 'payslip_run_id')
    def _check_dupl_payslip(self):
        if self.is_stc:
            dupl_stc = self.search(
                [('payslip_run_id', '=', self.payslip_run_id.id), ('employee_id', '=', self.employee_id.id),
                 ('is_stc', '=', True)]) - self
            invalid_stc = self.search(
                [('date_from', '<', self.date_from), ('employee_id', '=', self.employee_id.id), ('is_stc', '=', True)])
            if dupl_stc:
                raise ValidationError(
                    u"%s a déjà un STC pour la période %s" % (self.employee_id.name, self.payslip_run_id.name))
            elif invalid_stc:
                raise ValidationError(
                    u"%s ne peut pas avoir un STC postérieur à sa date de clôture de contrat" % (self.employee_id.name))
        else:
            dupl_payslip = self.search(
                [('payslip_run_id', '=', self.payslip_run_id.id), ('employee_id', '=', self.employee_id.id)]) - self
            if dupl_payslip:
                raise ValidationError(
                    u"%s a déjà un bulletin pour la période %s" % (self.employee_id.name, self.payslip_run_id.name))
        if self.payslip_run_id.state not in ['draft', 'pending', 'instance']:
            raise ValidationError(u"Vous ne pouvez pas ajouter un bulletin pour une période déjà validée.")

    @api.returns('hr.payslip.run')
    def get_payslip_run(self, date_from, date_to, company_id):
        return self.env['hr.payslip.run'].search(
            [('company_id', '=', company_id), ('date_start', '<=', date_from),
             ('date_end', '>=', date_to), ('state', 'in', ['draft', 'pending', 'instance'])], limit=1)

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_date(self):
        test = self.get_payslip_run(self.date_from, self.date_to, self.employee_id.company_id.id)
        self.payslip_run_id = self.get_payslip_run(self.date_from, self.date_to, self.employee_id.company_id.id)
        self.payslip_link_id = self.get_payslip_link_id()[0]

    @api.onchange('payslip_run_id')
    def onchange_run_id(self):
        if self.payslip_run_id:
            self.date_from = self.payslip_run_id.date_start
            self.date_to = self.payslip_run_id.date_end

    @api.one
    def get_payslip_link_id(self):
        return self.search(
            [('employee_id', '=', self.employee_id.id), ('date_to', '<', self.date_from)], order='date_from desc',
            limit=1)

    @api.multi
    def hr_close_sheet(self):
        for rec in self:
            if rec.state == 'validate':
                rec.write({'state': 'done'})

    @api.multi
    def hr_validate_sheet(self):
        """Move state only from verify to validate
        In other case it's will not work
        """
        if self.state == 'verify':
            if self.contract_id.monthly_hours_amount_id:
                if self.hr_timesheet_sheet_sheet_id and self.hr_timesheet_sheet_sheet_id.state != 'done':
                    raise UserError(_(
                        "La fiche de paie ne peut pas être validée car la feuille de temps de l'employé pour cette période n'a pas encore été approuvée."))
                if not self.hr_timesheet_sheet_sheet_id:
                    raise UserError(_("Aucune feuille de temps disponible asoociée à l'employé pour cette période."))
                else:
                    return self.write({'state': 'validate'})
            else:
                return self.write({'state': 'validate'})

    @api.multi
    def check_done(self):
        """
            Lock state from verify to done immediatly
        """
        res = super(HrPayslip, self).check_done()  # always True
        if res and self.state in ('draft', 'verify', 'instance', 'validate'):
            return False
        return res

    # @api.one
    # @api.depends('employee_id')
    # def _get_payment_mode(self):
    #     if self.contract_id:
    #         self.payment_mode = self.contract_id.payslip_payment_mode_id

    @api.onchange('contract_id')
    def onchange_contract(self):
        res = super(HrPayslip, self).onchange_contract()
        print("\n=== chg ctt res = %s" % res)
        return res

    @api.multi
    def get_org_sante_pat_amount(self):
        result = 0
        for rec in self.line_ids:
            if rec.code in ['ORGM_PAT']:
                result = rec.total
        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    @api.multi
    def hide_code_in_report(self):
        if self.contract_id.type_id.code == 'CSTG':
            result = ['SB',
                      'GROSS',
                      'CNAPS_PAT',
                      'RET_CNAPS_EMP',
                      'ORGM_PAT',
                      'RET_ORGM_EMP',
                      'IMPOSABLE',
                      'PAID_LEAVES',
                      'PAP',
                      'PRD',
                      'DED_ENFANT',
                      'IRSA',
                      'HT',
                      'H_BASIC',
                      'TJ',
                      'MSA',
                      'HSN',
                      'ALLOC',
                      'ECART_ARRONDI']
        else:
            result = ['CNAPS_PAT',
                      'NETAPAYER',
                      'HT',
                      'MSA',
                      'HSN',
                      'ORGM_PAT']
        NET1 = NET2 = 0
        for rec in self.line_ids:
            if rec.code in ['NET1']: NET1 = rec.total
            if rec.code in ['NET2']: NET2 = rec.total
        if NET1 == NET2:
            result.append('NET1')
            result.append('NET2')
        else:
            result.append('NET')

        return result

    @api.multi
    def get_cnaps_pat_amount(self):
        result = 0
        for rec in self.line_ids:
            if rec.code in ['CNAPS_PAT']:
                result = rec.total
        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    @api.multi
    def get_net_due(self):
        result = 0
        for rec in self.line_ids:
            if rec.code in ['NETAPAYER']:
                result = rec.total
        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    @api.multi
    def get_matricule(self):
        if self.employee_id.identification_cdi_id:  # != 0:
            return self.employee_id.identification_cdi_id
        else:
            return self.employee_id.identification_id

    @api.multi
    def get_ht(self):
        result = 0
        for rec in self.line_ids:
            if rec.code in ['HT']:
                result = rec.total
        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    def get_number_dayoff(self, date_from, date_to):
        from_date = date_from
        i = 0
        while from_date <= date_to:
            dayoff = self.env['training.holiday.period'].search(
                [('date_start', '<=', from_date), ('date_stop', '>=', from_date)])
            if dayoff:
                i += 1
            from_date = from_date + relativedelta(days=1)
        return i

    @api.multi
    def get_allocated_leaves(self):
        date_from = (
                datetime.strptime(str(self.date_from), "%Y-%m-%d") + relativedelta(months=-1, day=21,
                                                                                   days=-1)).strftime(
            '%Y-%m-%d %H:%M:%S')
        date_to = (datetime.strptime(str(self.date_from), "%Y-%m-%d") + relativedelta(day=20, days=-1)).strftime(
            '%Y-%m-%d %H:%M:%S')

        self._cr.execute(
            """ SELECT COALESCE(SUM(number_of_days),0) FROM hr_holidays WHERE type='add' AND state='validate' AND employee_id=%s and date_from BETWEEN %s and %s """,
            (self.employee_id.id, date_from, date_to,))
        result = self._cr.fetchone()[0]

        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    @api.multi
    def get_base(self, code):
        result = H_BASIC = HSN = 0
        for rec in self.line_ids:
            if rec.code in ['H_BASIC']:
                H_BASIC = rec.total
            if rec.code in ['HSN'] and code not in ['HMNUIT', 'HMDIM', 'HMJF']:
                HSN = rec.total
        if HSN > 33.6 and code == 'HS30':
            HSN = 33.6
        elif HSN < 33.6 and code == 'HS30':
            HSN = HSN
        if HSN > 33.6 and code == 'HS50':
            HSN = HSN - 33.6
        elif HSN < 33.6 and code == 'HS50':
            HSN = 0

        if HSN > 0 and code == 'HS30': result = H_BASIC * 0.3
        if HSN > 0 and code == 'HS50': result = H_BASIC * 0.5

        for rec in self.line_ids:
            if rec.code in ['HMNUIT'] and rec.total != 0 and code == 'HMNUIT': result = H_BASIC * 0.3
            if rec.code in ['HMDIM'] and rec.total != 0 and code == 'HMDIM': result = H_BASIC * 0.4
            if rec.code in ['HMJF'] and rec.total != 0 and code == 'HMJF': result = H_BASIC * 1
            if rec.code in ['PAID_LEAVES'] and rec.total != 0 and code == 'PAID_LEAVES': result = \
                [input.amount for input in self.input_line_ids if input.code in ['PAID_LEAVES']][0]
        return "{0:,.2f}".format(result).replace(',', ' ').replace('.', ',')

    @api.one
    @api.depends('employee_id', 'date_from', 'date_to')
    def _get_holidays(self):

        DATE_FORMAT = "%Y-%m-%d"
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        liste = []
        self.nb_leave = 0
        self.nb_leave_deductible = 0
        # date_to has to be greater than date_from
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        # get all holidays which are holidays request validated
        holis = self.env['hr.holidays'].search(
            [('employee_id', '=', self.employee_id.id), ('type', '=', 'remove'), ('state', '=', 'validate')])

        # convert self.date_from to a datetime type
        parse_date = datetime.strptime(self.date_from, DATE_FORMAT)

        # test if the month is january
        if parse_date.month - 1 == 0:
            d_from_str = str(parse_date.year - 1) + "-12-20"
            d_to_str = str(parse_date.year) + "-01-19"
        else:
            d_from_str = str(parse_date.year) + "-" + str(parse_date.month - 1) + "-20"
            d_to_str = str(parse_date.year) + "-" + str(parse_date.month) + "-19"

        # set the time's interval from days 20 of the previous month to days 19 of the current month
        d_from = datetime.strptime(d_from_str, DATE_FORMAT)
        d_to = datetime.strptime(d_to_str, DATE_FORMAT)

        for h in holis:
            h_d_from_source = datetime.strptime(h.date_from, DATETIME_FORMAT)
            h_d_from = h_d_from_source.replace(hour=0, minute=0, second=0)
            h_d_to_source = datetime.strptime(h.date_to, DATETIME_FORMAT)
            h_d_to = h_d_to_source.replace(hour=0, minute=0, second=0)

            # test if h_d_from is between days 20 of the previous month to days 19 of the current month
            if d_from <= h_d_from and d_to >= h_d_to:
                liste.append(h.id)
                nb_dayoff = self.get_number_dayoff(h_d_from, h_d_to)
                if h.holiday_status_id.deductible == False:
                    if not h.visible_payslip:
                        self.nb_leave += float((h_d_to - h_d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True:
                            self.nb_leave -= 0.5
                else:
                    if not h.visible_payslip:
                        self.nb_leave_deductible += float((h_d_to - h_d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True:
                            self.nb_leave_deductible -= 0.5

            # test if only the day_form of holiday is between days 20 of the previous month to days 19 of the current month
            elif d_from <= h_d_from and d_to >= h_d_from and d_to <= h_d_to:
                liste.append(h.id)
                nb_dayoff = self.get_number_dayoff(h_d_from, d_to)
                if h.holiday_status_id.deductible == False:
                    if not h.visible_payslip:
                        self.nb_leave += float((d_to - h_d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True and h.halfdayposition == "before":
                            self.nb_leave -= 0.5
                else:
                    if not h.visible_payslip:
                        self.nb_leave_deductible += float((d_to - h_d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True and h.halfdayposition == "before":
                            self.nb_leave_deductible -= 0.5

            # test if only the day_to of holiday is between days 20 of the previous month to days 19 of the current month
            elif d_from >= h_d_from and d_from <= h_d_to and d_to >= h_d_to:
                liste.append(h.id)
                nb_dayoff = self.get_number_dayoff(d_from, h_d_to)
                if h.holiday_status_id.deductible == False:
                    if not h.visible_payslip:
                        self.nb_leave += float((h_d_to - d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True and (h.halfdayposition == "after" or not h.halfdayposition):
                            h.halfdayposition = "after"
                            self.nb_leave -= 0.5
                else:
                    if not h.visible_payslip:
                        self.nb_leave_deductible += float((h_d_to - d_from).days + 1 - nb_dayoff)
                        if h.addhalfday == True and (h.halfdayposition == "after" or not h.halfdayposition):
                            h.halfdayposition = "after"
                            self.nb_leave_deductible -= 0.5

        self.leave_employee = [(6, 0, liste)]

    def refund_sheet(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        for payslip in self.browse(cr, uid, ids, context=context):
            id_copy = self.copy(cr, uid, payslip.id, {'credit_note': True, 'name': _('Refund: ') + payslip.name},
                                context=context)
            #             if payslip.hr_timesheet_sheet_sheet_id:
            #                 self.write(cr, uid, id_copy, {'hr_timesheet_sheet_sheet_id': payslip.hr_timesheet_sheet_sheet_id.id})
            self.signal_workflow(cr, uid, [id_copy], 'hr_verify_sheet')
            self.signal_workflow(cr, uid, [id_copy], 'process_sheet')

        form_id = mod_obj.get_object_reference(cr, uid, 'hr_payroll', 'view_hr_payslip_form')
        form_res = form_id and form_id[1] or False
        tree_id = mod_obj.get_object_reference(cr, uid, 'hr_payroll', 'view_hr_payslip_tree')
        tree_res = tree_id and tree_id[1] or False
        return {
            'name': _("Refund Payslip"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % [id_copy],
            'views': [(tree_res, 'tree'), (form_res, 'form')],
            'context': {}
        }

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super(HrPayslip, self).onchange_employee()
        if self.employee_id and self.date_from:
            slip_name = "Bulletin" if not self._context.get('default_is_stc') else "STC"
            self.name = ('%s') % (self.employee_id.name)
            self.payment_mode = self.employee_id.payment_mode
            self.bank_account_id = self.employee_id.bank_account_id
            self.payment_mobile = self.employee_id.payment_mobile
            self.tel_for_payment = self.employee_id.tel_for_payment
        contract_ids = self.get_contract(self.employee_id, self.date_from, self.date_to)
        if not contract_ids:
            return
        # opened_contract = self.employee_id.contract_ids.filtered(lambda c: c.state in ['open', 'renewed', 'active'])
        res_contract_ids = self.env['hr.contract'].browse(contract_ids)
        opened_contract = res_contract_ids.filtered(lambda c: c.state in ['open', 'renewed', 'active'])
        closed_contract = res_contract_ids.filtered(lambda c: c.state in ['close'])
        if self.is_stc:
            self.contract_id = closed_contract[0] if closed_contract else False
        else:
            self.contract_id = opened_contract[0] if opened_contract else False

        # self.contract_id = opened_contract if opened_contract.id in contract_ids else self.contract_id.browse(
        #     contract_ids[0])

    def onchange_employee_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False,
                             context=None):
        res = super(HrPayslip, self).onchange_employee_id(cr, uid, ids, date_from, date_to, employee_id, contract_id,
                                                          context)
        empolyee_obj = self.pool.get('hr.employee')
        employee_id = empolyee_obj.browse(cr, uid, employee_id, context=context)
        slip_name = "Bulletin" if not context.get('default_is_stc') else "STC"
        full_name = ('%s') % (employee_id.name)
        res['value'].update({'name': full_name})
        return res

    @api.model
    def convert_date_to_french_string(self, date):
        str_month = ['Janvier', u'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', u'Août', 'Septembre', 'Octobre',
                     'Novembre', u'Décembre']
        format_date = datetime.strptime(str(date), "%Y-%m-%d")
        mois = format_date.month
        annee = format_date.year
        return str_month[int(mois - 1)] + " " + str(annee)

    @api.one
    def make_verified(self):
        for input_id in self.input_line_ids:
            if input_id.color_button == 'orange': input_id.color_button = 'grey'
            if not input_id.color_button or input_id.color_button != 'green':
                input_id.with_context(from_button=True).change_color()
        self.state = 'verify'

    @api.one
    def make_rectified(self):
        is_pending = False
        for input_id in self.input_line_ids:
            if input_id.color_button == 'green':
                input_id.with_context(from_button=True).change_color()
            else:
                is_pending = True
        self.state = 'draft' if not is_pending else 'verify'
        self.computed_payslip = False

    @api.one
    def make_instanciated(self):
        self.state = 'instance'

    @api.one
    @api.depends('input_line_ids')
    def button_visibility(self):
        payslip_id = self._context.get('params').get('id')
        current_payslip = self.browse([payslip_id])
        current_payslip.computed_payslip = False
        if self.state in ['draft', 'verify'] and self.input_line_ids:
            if (any(input_id.color_button == 'green' for input_id in self.input_line_ids)):
                self.button_rectify_visible = True
            else:
                self.button_rectify_visible = False
            if (any(input_id.color_button in ['grey', 'orange'] or not input_id.color_button for input_id in
                    self.input_line_ids)):
                self.button_verify_visible = True
                self.button_submit_visible = False
                button_compute_visible = False
            else:
                self.button_verify_visible = False
                self.button_submit_visible = True
                if self.is_stc:
                    if self.contract_id.state == 'close':
                        button_compute_visible = True
                    else:
                        button_compute_visible = False
                else:
                    button_compute_visible = True
        elif self.state == 'instance':
            button_compute_visible = True
        else:
            self.button_verify_visible = False
            self.button_rectify_visible = False
            self.button_submit_visible = False
            button_compute_visible = False

        active_user = self.env.user
        in_group = lambda group: active_user.has_group(group)

        self.button_compute_visible = button_compute_visible and any(
            map(in_group, ['hr_copefrito_paie.group_system_admin', 'hr_copefrito_paie.group_pay_manager']))

    @api.one
    @api.depends('total_amount')
    def reset_computed_payslip(self):
        self.computed_payslip = False

    @api.one
    def mark_validate(self):
        if not self.computed_payslip:
            raise ValidationError(_('Please compute the paysilp'))
        context = self._context
        if not self.payslip_run_id.responsable.signature_img:
            raise UserError("La signature du responsable n'est pas configurée")
        self.state = 'validate'
        date_today = datetime.strptime(str(self.payslip_run_id.date_end), "%Y-%m-%d")

        # return a list of str from A to Z
        list_code_month = [chr(l).upper() for l in xrange(ord('a'), ord('z') + 1)]
        year_code = "%s" % (date_today.year % 10)
        month_code = list_code_month[date_today.month - 1]
        final_code = "%s%s" % (year_code, month_code,)

        if self.contract_id:
            service_code = self.contract_id.department_id.get_service_code()[0]
            final_code += service_code if not self.is_stc else "Z"

        if not context.get('from_payslip_run'):
            sorted_slip_ids = self.payslip_run_id.get_sorted_slip_ids()[0]
            self.number = final_code + sorted_slip_ids[self.id]

        return final_code

    @api.one
    def invalidate(self):
        if self.state == 'validate':
            self.state = 'draft'
        self.computed_payslip = False

    @api.multi
    def open_line_ids(self):
        domain = [('id', 'in', self.line_ids.ids)]
        view_id = self.env.ref('hr_copefrito_paie.view_hr_payslip_line_tree_inherit').id
        return {
            'type': 'ir.actions.act_window',
            'name': u'Résultats',
            'res_model': 'hr.payslip.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'domain': domain,
            'view_id': view_id
        }

    @api.one
    @api.depends('payslip_run_id.around_value')
    def compute_around_value(self):
        if self.payslip_run_id:
            self.around_value = self.payslip_run_id.around_value

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrPayslip, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        view_types = ['tree', 'form', 'kanban']
        if view_type in ['form', 'tree'] and result.get('toolbar') and result['toolbar'].get('print'):
            toolbar_form = result['toolbar']['print']
            i = 0
            new_toolbar_form = []
            for element in toolbar_form:
                xml_id = element.get('xml_id')
                if not self._context.get('default_is_stc') and xml_id != 'hr_copefrito_paie.copefrito_report_STC':
                    if self._context.get('lang') == 'fr_FR' and xml_id == 'hr_payroll.action_report_payslip':
                        element.update({
                            u'display_name': u'Feuille de paie',
                            u'name': u'Feuille de paie'
                        })
                    new_toolbar_form.append(element)
                if self._context.get('default_is_stc') and (xml_id == 'hr_copefrito_paie.copefrito_report_STC'):
                    new_toolbar_form.append(element)
                i += 1
            result['toolbar']['print'] = new_toolbar_form

        if not self._context.get('default_is_stc') or True:
            if not self.env.user.has_group('hr_copefrito_paie.group_pay_manager'):
                if view_type == 'tree':
                    for node in doc.xpath('//tree'):
                        node.set('create', 'false')
                        node.set('delete', 'false')
                if view_type == 'form':
                    for node in doc.xpath('//form'):
                        node.set('edit', 'false')

        result['arch'] = etree.tostring(doc)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'seq' in fields:
            fields.remove('seq')
        return super(HrPayslip, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                 lazy=lazy)

    @api.one
    def get_irsa_rate(self):
        line_ids = self.line_ids
        if line_ids:
            contract = self.contract_id
            company_id = contract.employee_id.company_id if not contract.employee_id.company_id.use_parent_param else contract.employee_id.company_id.parent_id
            imposable_rule = self.env.ref('hr_copefrito_paie.hr_payroll_rules_IMPOSABLE')
            imposable = line_ids.filtered(lambda l: l.salary_rule_id.id == imposable_rule.id).amount
            res = 100.0 if imposable <= company_id.seuil_irsa else company_id.taux_irsa
            return res
        return 0

    @api.onchange('employee_id')
    def set_payment_mode(self):
        if self.employee_id:
            self.payment_mode = self.employee_id.payment_mode

    @api.onchange('is_stc', 'employee_id', 'date_to', 'date_from')
    def dynamic_domain(self):
        domain_contract = [('employee_id', '=', self.employee_id.id), ('date_start', '<=', self.date_to), '|',
                           ('date_end', '>=', self.date_from), ('date_end', '=', False)]
        if self.is_stc:
            closed_contract = self.env['hr.contract'].search([('state', '=', 'close')])
            employee_ids = closed_contract.mapped('employee_id').ids
            domain_contract = [('id', 'in', closed_contract.ids)] + domain_contract
        else:
            opened_contract = self.env['hr.contract'].search([('state', 'in', ['open', 'renewed', 'active'])])
            employee_ids = opened_contract.mapped('employee_id').ids
            domain_contract = [('id', 'in', opened_contract.ids)] + domain_contract
        return {'domain': {'employee_id': [('id', 'in', employee_ids)],
                           'contract_id': domain_contract}}

    @api.model
    def set_decimal(self, dec):
        # return format(round(dec, 2), '.2f').replace(',', '.')
        return "{:,.2f}".format(round(abs(dec), 2)).replace(',', ' ').replace('.', ',')


class hr_holidays(models.Model):
    _inherit = 'hr.holidays'
    contract_id = fields.Many2one('hr.contract')


"""
__________________________________________________________________________________________

@Description : FUNCTION TO CREATE NEW VIEW NAMED "ETAT DE PAIE"
@Author: Sylvain Michel R.
@Begins on : 09/12/2016
@Latest update on : 28/12/2016
__________________________________________________________________________________________

"""


class hr_payslip_paid_state(models.Model):
    _name = 'hr.payslip.paid.state'
    _description = 'Etat de paie'
    _auto = False

    name = fields.Char(string=u'Réference du lots', required=True, copy=False, readonly=True, index=True, default='/')
    matricule = fields.Char(u'N° Matricule', readonly=True)
    employee = fields.Char(u'Nom et prénom', readonly=True)
    date_start = fields.Date(u'Date d\'embauche', readonly=True)
    date_end = fields.Date(u'Date de débauche', readonly=True)
    #     working_hours = fields.Float(u'Heures travaillées', readonly=True)
    #     diff_hours = fields.Float(u'Différence HT/HC', readonly=True)
    contract_qualification_id = fields.Many2one('hr.contract.qualification', u'Qualification', readonly=True)
    # payment_mode = fields.Many2one('hr.payslip.payment.mode', u'Mode de paiement', readonly=True)
    bank_id = fields.Many2one('res.bank', u'Banque', readonly=True)
    bic = fields.Char(u'Code banque', readonly=True)
    gab_code = fields.Char(u'Code guichet', readonly=True)
    acc_number = fields.Char(u'Numéro de compte', readonly=True)
    rib_key = fields.Char(u'RIB', readonly=True)
    name_code = fields.Char(u'Nom', readonly=True)
    code = fields.Char(u'Code', readonly=True)
    category = fields.Char(u'Catégorie salariale', readonly=True)
    quantity = fields.Float(u'Quantité')
    rate = fields.Float(u'Taux (%)')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, \
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    amount = fields.Monetary(u'Montant')
    total = fields.Monetary(u'Total')
    slip_date_from = fields.Date(u'Date début', readonly=True)
    slip_date_to = fields.Date(u'Date fin', readonly=True)
    slip_month = fields.Char('Mois', readonly=True)
    trimestre = fields.Char('Trimestre', readonly=True)
    payslip_id = fields.Many2one('hr.payslip', u'Bulletin', readonly=True)
    net_a_payer = fields.Monetary(u'Net à payer', readonly=True)
    org_medicaux_emp = fields.Monetary(u'Retenue organisme medical Employé', readonly=True)
    org_medicaux_pat = fields.Monetary(u'Charge Patronal organisme médical', readonly=True)
    employee_id = fields.Many2one('hr.employee', u'Employé', readonly=True)
    cot_irsa = fields.Monetary(u'Retenue IRSA', readonly=True)
    cnaps_emp = fields.Monetary(u'Retenue CNAPS Employé', readonly=True)
    cnaps_pat = fields.Monetary(u'CNAPS Patronal', readonly=True)
    slip_date = fields.Char('ANNEE-MOIS', readonly=True)
    job_name = fields.Char(u'Fonction', readonly=True)
    num_cnaps = fields.Char(u'N° CNAPS', readonly=True)
    # somme_avantage = fields.Monetary(u'Montant avantage', readonly=True)
    sequence = fields.Integer(u'Séquence', readonly=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', u'Règles salariales', readonly=True)
    salaire_base = fields.Monetary(u'Salaire de Base')
    salaire_mens = fields.Monetary(u'Salaire mensuel')
    taux_h = fields.Monetary(u'Taux horaire')
    taux_j = fields.Monetary(u'Taux journalier')
    ht = fields.Monetary(u'Heures travaillées')
    pre_a_payer = fields.Monetary(u'Préavis à payer')
    pre_deduc = fields.Monetary(u'Préavis déductible')
    h_supp = fields.Monetary(u'Heures Supplémentaire')
    h_supp_30 = fields.Monetary(u'HS à 30%')
    h_supp_50 = fields.Monetary(u'HS à 50%')
    h_maj_nuit = fields.Monetary(u'Heure majoré nuit')
    h_maj_dim = fields.Monetary(u'Heure majoré dimanche')
    abs_ded = fields.Monetary(u'Absences déductibles')
    h_maj_fer = fields.Monetary(u'Heure majoré jour férié')
    paid_leave = fields.Monetary(u'Congés Payés')
    rappel = fields.Monetary(u'Rappel sur période antérieur')
    salaire_brut = fields.Monetary(u'Salaire BRUT')
    imposable = fields.Monetary(u'Montant imposable')
    ded_enfant = fields.Monetary(u'Déduction pour enfant')
    m_avance15 = fields.Monetary(u'Montant avance quinzaine')
    au_ded = fields.Monetary(u'Autre déduction')
    avance_spe = fields.Monetary(u'Avance spécial')
    ret_total = fields.Monetary(u'Total Retenue Employé')
    net = fields.Monetary(u'Salaire Net')
    alloc = fields.Monetary(u'Allocation familliale')
    somme_avantage = fields.Monetary(u'Somme avantage')
    somme_prime = fields.Monetary(u'Somme prime')
    hc = fields.Float(u'Heures contrat', readonly=True)
    cat = fields.Char(u'Catégorie')
    agence = fields.Char(u'Agence', readonly=True)
    net1 = fields.Monetary(u'Salaire Net 1')
    net2 = fields.Monetary(u'Salaire Net 2')
    msa = fields.Monetary(u'Masse salariale')
    ecart_arr = fields.Monetary(u'Ecart arrondi')
    payment_mode = fields.Selection(
        [('mobile', 'Mobile'), ('bank', 'Virement'), ('check', 'Chèque'), ('cash', 'Espèces')],
        string=u"Mode de paiement")

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'hr_payslip_paid_state')
        cr.execute("""
            CREATE or REPLACE view hr_payslip_paid_state AS
                SELECT
                    pl.id,
                    pr.name AS name,
                    CASE
                        WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
                        ELSE CAST(emp.identification_cdi_id AS char)
                    END AS matricule,  
                    emp.name_related AS employee,
                    ag.name as agence,
                    p.date_from AS slip_date_from,
                    p.date_to AS slip_date_to,
                    c.date_start,
                    c.date_end,
                    c.contract_qualification_id,
                    c.payslip_payment_mode_id AS payment_mode,
                    rb.id AS bank_id,
                    rb.bic,
                    rpb.gab_code,
                    rpb.acc_number,
                    rpb.rib_key,
                    pl.sequence,
                    pl.name AS name_code,
                    pl.salary_rule_id,
                    pl.code AS code,
                    src.name AS category,
                    pl.quantity,
                    pl.rate,
                    rc.id AS currency_id,
                    pl.amount,
                    pl.total,
                    p.id AS payslip_id,
                    to_char(p.date_from, 'MM') AS slip_month,
                    CASE
                        WHEN to_char(p.date_from, 'MM')='01' OR to_char(p.date_from, 'MM')='02' OR to_char(p.date_from, 'MM')='03' THEN 'Trimestre 1'
                        WHEN to_char(p.date_from, 'MM')='04' OR to_char(p.date_from, 'MM')='05' OR to_char(p.date_from, 'MM')='06' THEN 'Trimestre 2'
                        WHEN to_char(p.date_from, 'MM')='07' OR to_char(p.date_from, 'MM')='08' OR to_char(p.date_from, 'MM')='09' THEN 'Trimestre 3'
                        WHEN to_char(p.date_from, 'MM')='10' OR to_char(p.date_from, 'MM')='11' OR to_char(p.date_from, 'MM')='12' THEN 'Trimestre 4'
                    END AS trimestre,
                    pl2.total as net_a_payer,
                    pl3.total as org_medicaux_emp,
                    pl4.total as org_medicaux_pat,
                    p.employee_id as employee_id,
                    pl5.total as cot_irsa,
                    pl6.total as cnaps_emp,
                    pl7.total as cnaps_pat,
                    to_char(p.date_from, 'YYYY-MM') AS slip_date,
                    jb.name as job_name,
                    emp.num_cnaps,
                    pl8.total as somme_avantage,
                    pl9.total as somme_prime,
                    pl10.total as salaire_base,
                    pl11.total as salaire_mens,
                    pl12.total as taux_h,
                    pl13.total as taux_j,
                    pl14.total as ht,
                    pl15.total as pre_a_payer,
                    pl16.total as pre_deduc,
                    pl17.total as h_supp,
                    pl18.total as h_supp_30,
                    pl19.total as h_supp_50,
                    pl20.total as h_maj_nuit,
                    pl21.total as h_maj_dim,
                    pl22.total as abs_ded,
                    pl23.total as h_maj_fer,
                    pl24.total as paid_leave,
                    pl25.total as rappel,
                    pl26.total as salaire_brut,
                    pl27.total as imposable,
                    pl28.total as ded_enfant,
                    pl29.total as m_avance15,
                    pl30.total as au_ded,
                    pl31.total as avance_spe,
                    pl32.total as ret_total,
                    pl33.total as net,
                    pl34.total as alloc,
                    hc.hours as hc,
                    hcq.name as cat,
                    pl35.total as net1,
                    pl36.total as net2,
                    pl37.total as msa,
                    pl38.total as ecart_arr
                FROM hr_payslip_line pl
                LEFT JOIN hr_payslip p on pl.slip_id=p.id
                LEFT JOIN hr_payslip_line pl2 on pl2.slip_id = p.id and pl2.code = 'NETAPAYER'
                LEFT JOIN hr_payslip_line pl3 on pl3.slip_id = p.id and pl3.code = 'RET_ORGM_EMP'
                LEFT JOIN hr_payslip_line pl4 on pl4.slip_id = p.id and pl4.code = 'ORGM_PAT'
                LEFT JOIN hr_payslip_line pl5 on pl5.slip_id = p.id and pl5.code = 'IRSA'
                LEFT JOIN hr_payslip_line pl6 on pl6.slip_id = p.id and pl6.code = 'RET_CNAPS_EMP'
                LEFT JOIN hr_payslip_line pl7 on pl7.slip_id = p.id and pl7.code = 'CNAPS_PAT'
                LEFT JOIN hr_payslip_run pr on pr.id=p.payslip_run_id
                LEFT JOIN hr_employee emp on emp.id=p.employee_id
                LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
                LEFT JOIN hr_contract c on c.id=p.contract_id
                LEFT JOIN monthly_hours_contract_data hc on hc.id = c.monthly_hours_amount_id
                LEFT JOIN hr_contract_qualification hcq on hcq.id = c.contract_qualification_id
                LEFT JOIN monthly_hours_contract_data mh on mh.id=c.monthly_hours_amount_id
                LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
                LEFT JOIN res_bank rb on rb.id=rpb.bank_id
                LEFT JOIN res_company rcp on rcp.id=p.company_id
                LEFT JOIN res_currency rc on rc.id=rcp.currency_id
                LEFT JOIN hr_job jb on jb.id = emp.job_id
                LEFT JOIN hr_salary_rule_category src on src.id=pl.category_id
                LEFT JOIN hr_payslip_line pl8 on pl8.slip_id = p.id and pl8.code = 'SAVANTAGE'
                LEFT JOIN hr_payslip_line pl9 on pl9.slip_id = p.id and pl9.code = 'SPRIME'
                LEFT JOIN hr_payslip_line pl10 on pl10.slip_id = p.id and pl10.code = 'SB'
                LEFT JOIN hr_payslip_line pl11 on pl11.slip_id = p.id and pl11.code = 'SME'
                LEFT JOIN hr_payslip_line pl12 on pl12.slip_id = p.id and pl12.code = 'H_BASIC'
                LEFT JOIN hr_payslip_line pl13 on pl13.slip_id = p.id and pl13.code = 'TJ'
                LEFT JOIN hr_payslip_line pl14 on pl14.slip_id = p.id and pl14.code = 'HT'
                LEFT JOIN hr_payslip_line pl15 on pl15.slip_id = p.id and pl15.code = 'PAP'
                LEFT JOIN hr_payslip_line pl16 on pl16.slip_id = p.id and pl16.code = 'PRD'
                LEFT JOIN hr_payslip_line pl17 on pl17.slip_id = p.id and pl17.code = 'HSN'
                LEFT JOIN hr_payslip_line pl18 on pl18.slip_id = p.id and pl18.code = 'HS30'
                LEFT JOIN hr_payslip_line pl19 on pl19.slip_id = p.id and pl19.code = 'HS50'
                LEFT JOIN hr_payslip_line pl20 on pl20.slip_id = p.id and pl20.code = 'HMNUIT'
                LEFT JOIN hr_payslip_line pl21 on pl21.slip_id = p.id and pl21.code = 'HMDIM'
                LEFT JOIN hr_payslip_line pl22 on pl22.slip_id = p.id and pl22.code = 'ABSDED'
                LEFT JOIN hr_payslip_line pl23 on pl23.slip_id = p.id and pl23.code = 'HMJF'
                LEFT JOIN hr_payslip_line pl24 on pl24.slip_id = p.id and pl24.code = 'PAID_LEAVES'
                LEFT JOIN hr_payslip_line pl25 on pl25.slip_id = p.id and pl25.code = 'RPA'
                LEFT JOIN hr_payslip_line pl26 on pl26.slip_id = p.id and pl26.code = 'GROSS'
                LEFT JOIN hr_payslip_line pl27 on pl27.slip_id = p.id and pl27.code = 'IMPOSABLE'
                LEFT JOIN hr_payslip_line pl28 on pl28.slip_id = p.id and pl28.code = 'DED_ENFANT'
                LEFT JOIN hr_payslip_line pl29 on pl29.slip_id = p.id and pl29.code = 'MAVANCE15'
                LEFT JOIN hr_payslip_line pl30 on pl30.slip_id = p.id and pl30.code = 'AUDED'
                LEFT JOIN hr_payslip_line pl31 on pl31.slip_id = p.id and pl31.code = 'AVANCESP'
                LEFT JOIN hr_payslip_line pl32 on pl32.slip_id = p.id and pl32.code = 'RET_TOTAL'
                LEFT JOIN hr_payslip_line pl33 on pl33.slip_id = p.id and pl33.code = 'NET'
                LEFT JOIN hr_payslip_line pl34 on pl34.slip_id = p.id and pl34.code = 'ALLOC'
                LEFT JOIN hr_payslip_line pl35 on pl35.slip_id = p.id and pl35.code = 'NET1'
                LEFT JOIN hr_payslip_line pl36 on pl36.slip_id = p.id and pl36.code = 'NET2'
                LEFT JOIN hr_payslip_line pl37 on pl37.slip_id = p.id and pl37.code = 'MSA'
                LEFT JOIN hr_payslip_line pl38 on pl38.slip_id = p.id and pl38.code = 'ECART_ARRONDI'
        """)

    @api.multi
    def write(self, vals):
        self._cr.execute("""
            CREATE or REPLACE RULE hr_payslip_paid_state_upd AS ON UPDATE TO hr_payslip_paid_state
                DO INSTEAD
                UPDATE hr_payslip_line
                   SET quantity = NEW.quantity,
                       rate = NEW.rate,
                       amount = NEW.amount,
                       total = NEW.total
                WHERE id = OLD.id            
            """)

        res = super(hr_payslip_paid_state, self).write(vals)
        return res

    @api.onchange('amount', 'quantity', 'rate')
    def onchange_value(self):
        self.total = (self.quantity * self.amount) * self.rate / 100
        return

    @api.model
    def fields_get(self, fields=None):
        fields_to_hide = ['currency_id'
                          ]
        # you can set this dynamically
        res = super(hr_payslip_paid_state, self).fields_get(fields)
        # if not self._context.has_key('hide_all_update_total'):
        for field in fields_to_hide:
            res[field]['selectable'] = False
        return res


class hr_salary_rule(models.Model):
    _inherit = 'hr.salary.rule'

    _order = "sequence, id"

    rubric_id = fields.Many2one("hr.payslip.rubric.config", u"Rubrique liée")
    non_taxable = fields.Boolean(string='Non taxable', help="The company's currency", readonly=True,
                                 related='rubric_id.non_taxable', store=True)


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _inherit = ['hr.payslip.input', 'mail.thread']
    _order = 'code_rubric,matricule'

    @api.one
    def _compute_is_pay_manager(self):
        context = self._context
        self.is_pay_manager = context['uid'] in self.env.ref('hr_copefrito_paie.group_pay_manager').users.ids

    @api.one
    @api.depends('rubric_id.state', 'payslip_id.state')
    def _onchange_is_readonly(self):
        self.is_readonly = self.rubric_id.state == 'validate' or self.payslip_id.state == 'validate'

    quantity = fields.Float(u'Quantité', default=0.0)
    amount2 = fields.Float(u'Montant', digits=dp.get_precision('Montant général'))
    product_uom = fields.Many2one('product.uom', u'Unité', related='rule_id.rubric_id.product_uom')
    is_invisible = fields.Boolean("Invisible", default=False)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id')
    name_employee_id = fields.Char(u'Nom Employé', related='employee_id.name')
    service = fields.Many2one('hr.department', related='employee_id.department_id')
    # matricule = fields.Integer("Matricule", related="employee_id.identification_cdi_id", store=True)
    matricule = fields.Char("Matricule", related="employee_id.identification_cdi_id", store=True)
    number = fields.Char("Bulletin", related="payslip_id.number")
    color_button = fields.Selection([('green', 'Vérifié'), ('orange', 'Mise en attente'), ('grey', 'Brouillon')],
                                    'Couleur', default='grey')
    state = fields.Selection([('draft', 'Brouillon'), ('waiting', 'Mise en attente'), ('verified', u'Vérifié')], 'Etat',
                             default=False)
    rule_id = fields.Many2one('hr.salary.rule', string=u"Règle")
    # code_rubric = fields.Integer("Code", related="rule_id.rubric_id.code", store=True)
    code_rubric = fields.Char("Code", related="rule_id.rubric_id.code", store=True)
    rubric_id = fields.Many2one('hr.payslip.rubric', string=u"Rubrique")
    surname_employee = fields.Char("Surnom", related='employee_id.surname')
    job = fields.Many2one("hr.job", string=u"Poste", related="employee_id.job_id", store=True)
    is_pay_manager = fields.Boolean(compute=_compute_is_pay_manager)
    # amount_str = fields.Char(string=u"Montant")
    code_service = fields.Char(related='service.code_service', string='Service')
    is_readonly = fields.Boolean(string="Is readonly")
    active = fields.Boolean(string="Active", default=True)

    @api.model
    def create(self, vals):
        res = super(HrPayslipInput, self).create(vals)
        if not res.color_button:
            res.color_button = 'grey'
        return res

    @api.multi
    def write(self, vals):
        old_values = {}
        for input_id in self:
            if input_id.rubric_id.state == 'validate' or input_id.payslip_id.state == 'validate':
                if vals.has_key('amount2'):
                    del vals['amount2']
                if vals.has_key('amount'):
                    del vals['amount']
            if vals.has_key('amount') or vals.has_key('quantity') or vals.has_key('product_uom'):
                old_quantity = input_id.quantity
                old_amount = input_id.amount
                old_product_uom = input_id.product_uom.name
                old_values[input_id.id] = {"amount": old_amount, "quantity": old_quantity,
                                           "product_uom": old_product_uom or ""}
        res = super(HrPayslipInput, self).write(vals)
        for input_id in self:
            if vals.has_key('amount') or vals.has_key('quantity') or vals.has_key('product_uom'):
                MailTemplate = self.env['mail.template']
                body_html = "<p><strong>Entrée modifiée</strong><br/>Matricule: " + str(
                    input_id.matricule) + "<br/>Employé: " + input_id.employee_id.name.encode('utf-8') + "<ul>"
                if vals.has_key('amount'):
                    body_html += "<li>Montant: " + str(old_values.get(input_id.id)["amount"]) + " &rarr; " + str(
                        input_id.amount) + "</li>"
                if vals.has_key('quantity'):
                    body_html += "<li>Quantité: " + str(old_values.get(input_id.id)["quantity"]) + " &rarr; " + str(
                        input_id.quantity) + "</li>"
                if vals.has_key('product_uom'):
                    unit = old_values.get(input_id.id)["product_uom"].encode("utf-8")
                    new_unit = input_id.product_uom.name.encode("utf-8") if input_id.product_uom else ""
                    body_html += "<li>Unité: %s &rarr; %s</li>" % (unit, new_unit)
                body_html += "</ul></p>"
                notif = MailTemplate.render_template(body_html, 'hr.payslip.input', input_id.id)
                input_id.rubric_id.message_post(body=notif, subtype='mail.mt_note')
        return res

    @api.one
    def change_color(self):
        if self.rubric_id.state not in ['validate', 'closed'] and self.payslip_id.state not in ['waiting',
                                                                                                'done', 'cancel']:

            employee_name = self.employee_id.name.encode("utf-8")
            body_html = "<p><strong>Entrée modifiée</strong><br/>Matricule: " + str(
                self.matricule) + "<br/>Employé: " + employee_name + "<ul>"
            if not self.color_button or self.color_button == 'grey':
                self.color_button = 'green'
                body_html += "<li>Etat: Brouillon &rarr; Vérifié</li>"
            else:
                old_color = "Vérifié" if self.color_button == 'green' else "Mise en attente"
                body_html += "<li>Etat: %s &rarr; Brouillon</li>" % (old_color)
                self.color_button = 'grey'
            body_html += "</ul></p>"
            # don't track edit if click on button Verify or Rectify
            if not self._context.get('from_button'):
                self.rubric_id.message_post(body=body_html, subtype='mail.mt_note')

            if self.rubric_id:
                input_ids = self.search([('rubric_id', '=', self.rubric_id.id)])
                if (any(input_id.color_button == 'green' for input_id in input_ids)):
                    self.rubric_id.state = 'pending'
                else:
                    self.rubric_id.state = 'draft'

            if self.payslip_id:
                input_ids = self.search([('payslip_id', '=', self.payslip_id.id)])
                if (any(input_id.color_button == 'green' for input_id in input_ids)):
                    self.payslip_id.state = 'verify'
                else:
                    self.payslip_id.state = 'draft'
        if not self._context.get('from_button'):
            self.env['bus.bus'].sendone("bullet_refresh", "test")

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        '''
            This function replace the old function in order to not display code in sum in group by.
        '''
        if context is None:
            context = {}
        self.check_access_rights(cr, uid, 'read')
        query = self._where_calc(cr, uid, domain, context=context)
        fields = fields or self._columns.keys()

        groupby = [groupby] if isinstance(groupby, basestring) else groupby
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [
            self._read_group_process_groupby(cr, uid, gb, query, context=context)
            for gb in groupby_list
        ]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(cr, uid, query, 'read', context=context)
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            groupby_def = self._columns.get(gb) or (self._inherit_fields.get(gb) and self._inherit_fields.get(gb)[2])
            assert groupby_def and groupby_def._classic_write, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
            if not (gb in self._fields):
                # Don't allow arbitrary values, as this would be a SQL injection vector!
                raise UserError(_(
                    'Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.') % (
                                    gb,))

        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence', 'code_rubric', 'matricule', 'quantity')
            if f not in groupby_fields
            if f in self._fields
            if self._fields[f].type in ('integer', 'float', 'monetary')
            if getattr(self._fields[f].base_field.column, '_classic_write', False)
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator or 'sum',
            self._inherits_join_calc(cr, uid, self._table, f, query, context=context),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(cr, uid, order, aggregated_fields, annotated_groupbys,
                                                                query, context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.id) AS id, count(%(table)s.id) AS %(count_field)s %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        cr.execute(query, where_clause_params)
        fetched_data = cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        many2onefields = [gb['field'] for gb in annotated_groupbys if gb['type'] == 'many2one']
        if many2onefields:
            data_ids = [r['id'] for r in fetched_data]
            many2onefields = list(set(many2onefields))
            data_dict = {d['id']: d for d in self.read(cr, uid, data_ids, many2onefields, context=context)}
            for d in fetched_data:
                d.update(data_dict[d['id']])

        data = map(lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict, context) for k, v in r.iteritems()},
                   fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, groupby_dict, domain, context) for d in
                  data]
        if lazy and groupby_fields[0] in self._group_by_full:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way 
            result = self._read_group_fill_results(cr, uid, domain, groupby_fields[0],
                                                   groupby[len(annotated_groupbys):],
                                                   aggregated_fields, count_field, result, read_group_order=order,
                                                   context=context)

        return result

    @api.one
    @api.onchange('amount2', 'quantity')
    def compute_amount(self):
        if self.employee_id.company_id.automatic_compute_payslip_input:
            self.amount = self.amount2 * self.quantity
        else:
            self.amount = self.amount2

    # @api.onchange('amount_str')
    # def onchange_amount_str(self):
    #     if self.amount_str:
    #         str_value = self.amount_str.replace(',', '.')
    #         try:
    #             self.amount2 = float(str_value)
    #         except ValueError:
    #             self.amount2 = 0
    #             raise ValidationError('Mauvais format saisie')


class hr_payslip_line(models.Model):
    _inherit = 'hr.payslip.line'

    rubric_id = fields.Many2one('hr.payslip.rubric', "Rubrique")
    number = fields.Char("Bulletin", related="slip_id.number")
    # matricule = fields.Integer("Matricule", related="employee_id.identification_cdi_id")
    matricule = fields.Char("Matricule", related="employee_id.identification_cdi_id")
    service = fields.Many2one("hr.department", related="employee_id.department_id", string=u"Service")
    # code_rubric = fields.Integer("Code", related="salary_rule_id.rubric_id.code")
    code_rubric = fields.Char("Code", related="salary_rule_id.rubric_id.code")
    surname_employee = fields.Char("Surnom", related="employee_id.surname")
    job = fields.Many2one("hr.job", string=u"Poste", related="employee_id.job_id")
    the_quantity = fields.Char("Nombre", compute='get_quantity')
    the_quantity_float = fields.Float("Nombre", compute='get_quantity')
    base = fields.Char("base", compute="get_base")
    input_id = fields.Many2one('hr.payslip.input', compute='get_input')
    code_service = fields.Char(related='service.code_service', string='Service')
    active = fields.Boolean(string="active", default=True)
    number_hours = fields.Float(related='input_id.quantity')

    @api.depends('slip_id')
    @api.one
    def get_quantity(self):
        # for record in self:
        # if record.code_rubric == '100' or record.code_rubric == '199':
        #     if record.slip_id.monthly_hours_contract_info.hours:
        #         record.the_quantity = record.slip_id.monthly_hours_contract_info.hours
        # elif record.code_rubric == '211':
        #     if record.slip_id.nb_leave:
        #         record.the_quantity = record.slip_id.nb_leave

        if self.rubric_id.paylip_rubric_conf_id.id not in self.slip_id.contract_id.rubric_ids.mapped(
                'rubric_conf').ids:
            the_quantity = self.input_id.quantity
        else:
            is_incomplete, base_amount = \
                self.slip_id.contract_id.check_incomplete_month(self.slip_id.date_from, self.slip_id.date_to)[0]
            if is_incomplete:
                the_quantity = base_amount.get("qty_" + str(self.rubric_id.paylip_rubric_conf_id.id), 0)
            else:
                the_quantity = self.slip_id.monthly_hours_contract_info.hours
        self.the_quantity_float = round(float(the_quantity), 2)
        self.the_quantity = self.slip_id.set_decimal(the_quantity)

    @api.depends('slip_id')
    @api.one
    def get_base(self):
        # if self.code_rubric == '100' or self.code_rubric == '199':
        #     if self.the_quantity > 0:
        #         self.base = self.amount / self.the_quantity
        # if self.code_rubric == '211':
        #     if self.the_quantity > 0:
        #         self.base = self.amount / self.the_quantity
        # if self.code_rubric == '731':
        #     if self.slip_id.taux_cnaps_info > 0:
        #         self.base = (self.amount * 100) / self.slip_id.taux_cnaps_info
        # if self.code_rubric == '732':
        #     if self.slip_id.taux_om_emp_info > 0:
        #         self.base = (self.amount * 100) / self.slip_id.taux_om_emp_info
        # if self.code_rubric == '745':
        #     if self.slip_id.company_id.taux_irsa > 0:
        #         if self.amount != 2000:
        #             self.base = self.slip_id.company_id.taux_irsa
        #         else:
        #             self.base = 2000
        # def compute_base_reg(company_id, field_plafond, field_taux,):

        payslip = self.slip_id
        contract = payslip.contract_id
        company_id = contract.employee_id.company_id if not contract.employee_id.company_id.use_parent_param else contract.employee_id.company_id.parent_id

        basic_rule = self.env.ref('hr_copefrito_paie.hr_salary_rule_BRUT')
        basic_amount = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == basic_rule.id).amount

        base_value = 0.0
        if self.code_rubric == '731':
            brut = payslip.line_ids.filtered(lambda l: l.code_rubric == 'ST1').amount
            base_value = brut if brut <= company_id.plafond_cnaps else company_id.plafond_cnaps
        elif self.code_rubric == '732':
            base_value = basic_amount
        elif self.code_rubric == '745':
            irsa_rule = self.env.ref('hr_copefrito_paie.hr_payroll_rules_IMPOSABLE')
            irsa_amount = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == irsa_rule.id).amount
            base_value = irsa_amount
        #     cnaps_rule = self.env.ref('hr_copefrito_paie.hr_payroll_rules_CNAPS_EMP')
        #     cnaps_amount = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == cnaps_rule.id).amount
        #     osie_rule = self.env.ref('hr_copefrito_paie.hr_payroll_rules_RET_ORGM_EMP')
        #     osie_amount = payslip.line_ids.filtered(lambda l: l.salary_rule_id.id == osie_rule.id).amount
        #     base_value = ((int(basic_amount + cnaps_amount + osie_amount)) / 100) * 100
        elif self.code_rubric == '100':
            base_value = round(self.amount / self.input_id.quantity, 2) if self.input_id.quantity != 0 else round(
                self.amount / self.the_quantity_float, 2)
        else:
            base_value = round(self.amount / self.the_quantity_float, 2) if self.the_quantity_float != 0 else 0
        # self.base = format(round(float(base_value), 2), '.2f')
        self.base = self.slip_id.set_decimal(base_value)

    @api.one
    @api.depends('rubric_id')
    def get_input(self):
        self.input_id = self.rubric_id.input_ids.filtered(lambda x: x.employee_id.id == self.employee_id.id)
