# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv
from openerp.exceptions import UserError
from openerp.tools.translate import _

import datetime
import time
from datetime import timedelta, datetime, date
from dateutil.relativedelta import relativedelta
from openerp.exceptions import ValidationError
import werkzeug
from urlparse import urljoin
from calendar import monthrange
from lxml import etree
import openerp.addons.decimal_precision as dp

from datetime import datetime, timedelta


class hr_contract(models.Model):
    _inherit = 'hr.contract'

    @api.multi  ##-
    def write(self, vals):
        def generate_mat():

            # ___________________________________________________________________________________________|

            # ---------------------------  GENERATE MATRICULE VALUE IF NOT SET --------------------------|
            # ___________________________________________________________________________________________|

            if vals.has_key('type_id') and self.env['hr.contract.type'].search([('id', '=', vals['type_id'])]).code in [
                'CSTG']:
                incr_number = self.env['ir.sequence'].next_by_code('mat_stag')
                if incr_number:
                    if not self.employee_id.identification_id:
                        self.employee_id.write({'identification_id': incr_number})
                else:
                    raise UserError(_(u'Pas de séquence trouvé pour le contract stagiaire!'))
            if vals.has_key('type_id') and self.env['hr.contract.type'].search([('id', '=', vals['type_id'])]).code in [
                'CDI']:
                incr_number = self.env['ir.sequence'].next_by_code('mat_cdi')
                if incr_number:
                    if not self.employee_id.identification_cdi_id:  # or self.employee_id.identification_cdi_id == 0:
                        self.employee_id.write({'identification_cdi_id': incr_number})
                else:
                    raise UserError(_(u'Pas de séquence trouvé pour le contract CDI!'))

            NUMBER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
            if vals.has_key('num_contract'):
                if self.search([('num_contract', '=', vals['num_contract'])]):
                    raise UserError(_(u'Numéro contrat déjà existant'))
                # else:
                #     if len(vals['num_contract']) != 4 or not (all (n in NUMBER for n in vals['num_contract'])):
                #         raise UserError(_(u'Le numéro contrat devrait contenir 4 chiffres'))

        if vals.get('status') == 'journalier':
            vals.update({'num_contract': self.env['ir.sequence'].next_by_code('jr_contract')})
        if vals.get('status') == 'permanent':
            vals.update({'num_contract': self.env['ir.sequence'].next_by_code('pr_contract')})
        current_state = vals.get('state', False)
        old_vrbl_rub_dic = {}
        contract_status = {}
        for rec in self:
            old_vrbl_rub_dic[rec.id] = rec.variable_rubric_ids.ids
            contract_status[rec.id] = rec.status
            # get the contract of the current employee with state == 'open'
            contract_state_open = rec.employee_id.contract_ids.filtered(
                lambda c: c.state in ['open', 'renewed', 'active']) - rec
            current_date_end = vals.get('date_end', rec.date_end)
            if not current_date_end:
                if current_state and current_state == "close":
                    raise osv.except_osv(u'OUPS!',
                                         u'En état "Expiré", il faut renseigner la date de fin dans l\'intervalle de date "Durée"')
                elif current_state and current_state in ['open', 'renewed', 'active']:
                    if contract_state_open:
                        raise osv.except_osv(u'OUPS!', u'Un employé ne peut pas avoir plusieurs contrats en cours')
                    else:
                        current_date = time.strftime("%Y-%m-%d")
                        current_date_start = vals.get('trial_date_start', rec.trial_date_start) or vals.get(
                            'date_start', rec.date_start)
                        if vals.get('status') == 'permanent' and current_date_start > current_date:
                            raise osv.except_osv(u'OUPS!',
                                                 u'La date début du contrat doit être inférieur à la date du jour')
                    # else:
                    #     rec.employee_id.write(vals_employee)
                    # rec.employee_id.department_id = vals.get('department_id', rec.department_id)
                    # rec.employee_id.job_id = vals.get('job_id', rec.job_id)
                    # rec.employee_id.code_poste = vals.get('code_poste', rec.code_poste)
                    # rec.employee_id.code_service = vals.get('code_poste', rec.code_service)
                    # rec.employee_id.csp_id = vals.get('contract_qualification_id', rec.contract_qualification_id)

            generate_mat()

        res = super(hr_contract, self).write(vals)

        for rec in self:
            # if current_state and current_state in ['open', 'renewed', 'active']:
            if rec.state in ['open', 'renewed', 'active']:
                vals_employee = {
                    'job_id': vals.get('job_id', rec.job_id.id),
                    'code_poste': vals.get('code_poste', rec.code_poste.id),
                    'code_service': vals.get('code_service', rec.code_service.id),
                    'department_id': vals.get('department_id', rec.department_id.id),
                    'csp_id': vals.get('contract_qualification_id', rec.contract_qualification_id.id),
                    'identification_cdi_id': rec.employee_id.identification_cdi_id
                }
                rec.employee_id.write(vals_employee)

            # if vals.has_key('status') and old_vrbl_rub_dic[rec.id] != rec.status:
            #     rec.onchange_status()

            if vals.has_key('additional_hour'):
                action = 4 if vals.get('additional_hour') and rec.status == 'permanent' else 3
                self.env.ref('hr_copefrito_paie.RUBRIC_201').write({
                    'contract_ids': [(action, rec.id)]
                })

            rec.set_base_salary()

        return res

    # @api.multi
    # def count_mail_sent_today(self):
    # 	today = dt.today().isoformat().split('T')[0]
    # 	doms = [('sent', '>=', today)]
    # 	total_sent_mail_today = self.env['mail.mail.statistics'].search_count(doms)
    # 	return total_sent_mail_today

    @api.one
    def onchange_status(self):
        if self.status == 'permanent':
            vrbl_rubric = self.env['hr.payslip.rubric.config'].search(
                [('classe_id.code', 'in', ['2', '5', '6', '8']), ('type', '=', 'normal'),
                 ('status', 'in', ['mixte', 'permanent'])])
            for rub in vrbl_rubric:
                rub.contract_ids = [(4, self.id)]
            vrbl_rubric_unlink = self.env['hr.payslip.rubric.config'].search(
                [('type', '=', 'normal'), ('status', '=', 'journalier')])
            for rub in vrbl_rubric_unlink:
                rub.contract_ids = [(3, self.id)]
        elif self.status == 'journalier':
            vrbl_rubric = self.env['hr.payslip.rubric.config'].search(
                [('classe_id.code', 'in', ['2', '5', '6', '8']), ('type', '=', 'normal'),
                 ('status', 'in', ['mixte', 'journalier'])])
            for rub in vrbl_rubric:
                rub.contract_ids = [(4, self.id)]
            vrbl_rubric_unlink = self.env['hr.payslip.rubric.config'].search(
                [('type', '=', 'normal'), ('status', '=', 'permanent')])
            for rub in vrbl_rubric_unlink:
                rub.contract_ids = [(3, self.id)]
        else:
            self.env['hr.payslip.rubric.config'].search([('status', '=', 'normal')]).write({
                'contract_ids': [(3, self.id)]
            })

    @api.model
    def set_reminder_trial_end(self):
        sent = 0
        mail_limit = 1000
        contract_obj = self.env['hr.contract'].search([('enable_notifications', '=', True)])
        if contract_obj:
            for rec in contract_obj.filtered(lambda x: x.trial_is_end):
                if sent < mail_limit:
                    template = 'hr_copefrito_paie.email_template_notification_trial_expired_reminder'
                    self.send_mail(rec.id, template)
                    sent += 1
                elif sent >= mail_limit:
                    mail_mail_obj = self.env['mail.mail']
                    template = self.env.ref('hr_copefrito_paie.email_template_notification_trial_expired_reminder')
                    values = template.with_context().generate_email(rec.id)
                    values['email_from'] = self.env.user.company_id.email
                    pay_manager_group = self.env.ref('hr_copefrito_paie.group_pay_manager')
                    recipient_ids = []
                    for pay_manager in pay_manager_group.users:
                        if self.browse(rec.id).employee_id.company_id.id in pay_manager.company_ids.ids:
                            recipient_ids.append((4, pay_manager.partner_id.id))
                    values['recipient_ids'] = recipient_ids
                    values['state'] = 'outgoing'
                    msg_id = mail_mail_obj.create(values)
                    mail_thread = self.env['mail.thread']
                    mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'],
                                             partner_ids=recipient_ids)

    @api.model
    def set_reminder_renew_trial_end(self):
        sent = 0
        mail_limit = 1000
        contract_obj = self.env['hr.contract'].search([('enable_notifications', '=', True)])
        if contract_obj:
            for rec in contract_obj.filtered(lambda x: x.renew_trial_is_end):
                if sent < mail_limit:
                    template = 'hr_copefrito_paie.email_template_notification_renew_trial_expired_reminder'
                    self.send_mail(rec.id, template)
                    sent += 1
                elif sent >= mail_limit:
                    mail_mail_obj = self.env['mail.mail']
                    template = self.env.ref(
                        'hr_copefrito_paie.email_template_notification_renew_trial_expired_reminder')
                    values = template.with_context().generate_email(rec.id)
                    values['email_from'] = self.env.user.company_id.email
                    pay_manager_group = self.env.ref('hr_copefrito_paie.group_pay_manager')
                    recipient_ids = []
                    for pay_manager in pay_manager_group.users:
                        if self.browse(rec.id).employee_id.company_id.id in pay_manager.company_ids.ids:
                            recipient_ids.append((4, pay_manager.partner_id.id))
                    values['recipient_ids'] = recipient_ids
                    values['state'] = 'outgoing'
                    msg_id = mail_mail_obj.create(values)
                    mail_thread = self.env['mail.thread']
                    mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'],
                                             partner_ids=recipient_ids)

    @api.model
    def set_reminder_breastfeeding_end(self):
        sent = 0
        mail_limit = 1000
        contract_obj = self.env['hr.contract'].search([('enable_notifications', '=', True)])
        if contract_obj:
            for rec in contract_obj.filtered(lambda x: x.allaitement_is_end):
                if sent < mail_limit:
                    template = 'hr_copefrito_paie.email_template_notification_allaitement_expired_reminder'
                    self.send_mail(rec.id, template)
                    sent += 1
                elif sent >= mail_limit:
                    mail_mail_obj = self.env['mail.mail']
                    template = self.env.ref(
                        'hr_copefrito_paie.email_template_notification_allaitement_expired_reminder')
                    values = template.with_context().generate_email(rec.id)
                    values['email_from'] = self.env.user.company_id.email
                    pay_manager_group = self.env.ref('hr_copefrito_paie.group_pay_manager')
                    recipient_ids = []
                    for pay_manager in pay_manager_group.users:
                        if self.browse(rec.id).employee_id.company_id.id in pay_manager.company_ids.ids:
                            recipient_ids.append((4, pay_manager.partner_id.id))
                    values['recipient_ids'] = recipient_ids
                    values['state'] = 'outgoing'
                    msg_id = mail_mail_obj.create(values)
                    mail_thread = self.env['mail.thread']
                    mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'],
                                             partner_ids=recipient_ids)

    @api.model
    def create(self, vals):
        NUMBER = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        # check if num_contract already exist
        if vals.get('status') == 'journalier':
            vals.update({'num_contract': self.env['ir.sequence'].next_by_code('jr_contract')})
        if vals.get('status') == 'permanent':
            vals.update({'num_contract': self.env['ir.sequence'].next_by_code('pr_contract')})
        if vals.has_key('num_contract'):
            if self.search([('num_contract', '=', vals['num_contract'])]):
                raise UserError(_(u'Numéro contrat déjà existant'))
            # elif vals.get('num_contract'):
            #     if len(vals['num_contract']) != 4 or not (all(n in NUMBER for n in vals['num_contract'])):
            #         raise UserError(_(u'Le numéro contrat devrait contenir 4 chiffres'))

        result = super(hr_contract, self).create(vals)

        # ___________________________________________________________________________________________|

        # ---------------------------  GENERATE MATRICULE VALUE IF NOT SET --------------------------|
        # ___________________________________________________________________________________________|

        if vals.has_key('type_id') and self.env['hr.contract.type'].search([('id', '=', vals['type_id'])]).code in [
            'CSTG']:
            incr_number = self.env['ir.sequence'].next_by_code('mat_stag')
            if incr_number:
                if vals.has_key('employee_id') and not self.env['hr.employee'].search(
                        [('id', '=', vals['employee_id'])]).identification_id:
                    self.env['hr.employee'].search([('id', '=', vals['employee_id'])]).write(
                        {'identification_id': incr_number})
            else:
                raise UserError(_(u'Pas de séquence trouvé pour le contract stagiaire!'))
        if vals.has_key('type_id') and self.env['hr.contract.type'].search([('id', '=', vals['type_id'])]).code in [
            'CDI']:
            incr_number = self.env['ir.sequence'].next_by_code('mat_cdi')
            if incr_number:
                if vals.has_key('employee_id') and (
                        not self.env['hr.employee'].search([('id', '=', vals['employee_id'])]).identification_cdi_id
                        or not self.env['hr.employee'].search(
                    [('id', '=', vals['employee_id'])]).identification_cdi_id):
                    self.env['hr.employee'].search([('id', '=', vals['employee_id'])]).write(
                        {'identification_cdi_id': incr_number})
            else:
                raise UserError(_(u'Pas de séquence trouvé pour le contract CDI!'))

        # generate rubric fixe when creating new contract
        # rubric_ids = self.env['hr.payslip.rubric.config'].search([('type', '=', 'fixe')])
        # vals_rubrics = []
        # amount = 0
        # if result.employee_id.company_id.compute_base_salary == 'yes' and not result.contract_qualification_id.is_hc:
        #     amount = result.base_salary
        # vals_rubrics.append((0, 0, {'rubric_conf': self.env.ref('hr_copefrito_paie.RUBRIC_100').id, 'montant': amount}))
        # vals_rubrics.append((0, 0, {'rubric_conf': self.env.ref('hr_copefrito_paie.RUBRIC_100').id, 'montant': amount}))
        # for rubric in rubric_ids:
        #     rubric_in_domain = True
        #     if rubric.company_ids and self.env['hr.employee'].search(
        #             [('id', '=', vals['employee_id'])]).company_id not in rubric.company_ids: rubric_in_domain = False
        #     if rubric.hr_department_ids and result.department_id not in rubric.hr_department_ids.ids: rubric_in_domain = False
        #     if rubric_in_domain: vals_rubrics.append((0, 0, {'rubric_conf': rubric.id, 'montant': 0}))
        # if rubric_ids: result.write({'rubric_ids': vals_rubrics})

        # result.write({'rubric_ids': [(0,0, {'rubric_conf' : self.env.ref('hr_copefrito_paie.RUBRIC_100').id, 'montant' : amount})]})

        # status_list = ['mixte']
        # if result.status:
        #     status_list.append(result.status)
        #     vrbl_rubric = self.env['hr.payslip.rubric.config'].search(
        #         [('classe_id.code', 'in', ['2', '5', '6', '8']), ('type', '=', 'normal'),
        #          ('status', 'in', status_list)])
        #     if not result.additional_hour:
        #         vrbl_rubric -= self.env.ref('hr_copefrito_paie.RUBRIC_201')
        #     # the function write in hr.payslip.rubric.config will add directly itself in the contract
        #     vrbl_rubric.write({'contract_ids': [(4, result.id)]})

        result.set_base_salary()
        result.onchangeStatus()

        return result

    @api.one
    @api.onchange('status')
    def onchangeStatus(self):
        if self.status:
            # variable rubric
            status_list = ['mixte', self.status]
            vrbl_rubric = self.env['hr.payslip.rubric.config'].search(
                [('classe_id.code', 'in', ['2', '5', '6', '8']), ('type', '=', 'normal'),
                 ('status', 'in', status_list)])
            if not self.additional_hour:
                vrbl_rubric -= self.env.ref('hr_copefrito_paie.RUBRIC_201')
            self.variable_rubric_ids = [(6, 0, vrbl_rubric.ids)]

            # fixed rubric
            rubric_ids = self.env['hr.payslip.rubric.config'].search([('type', '=', 'fixe')])
            vals_rubrics = []
            amount = 0
            if self.employee_id.company_id.compute_base_salary == 'yes' and not self.contract_qualification_id.is_hc:
                amount = self.base_salary
            self.rubric_ids = [(6, 0, [])]
            vals_rubrics.append(
                (0, 0, {'rubric_conf': self.env.ref('hr_copefrito_paie.RUBRIC_100').id, 'montant': amount, 'active': True}))
            for rubric in rubric_ids:
                vals_rubrics.append((0, 0, {'rubric_conf': rubric.id, 'montant': 0, 'active': True}))
            self.rubric_ids = vals_rubrics

        else:
            self.variable_rubric_ids = False
            self.rubric_ids = False

    @api.one
    def set_base_salary(self):
        base_salary = self.rubric_ids.filtered(lambda r: r.rubric_conf == self.env.ref('hr_copefrito_paie.RUBRIC_100'))
        amount = base_salary.montant if base_salary else 0
        if self.employee_id.company_id.compute_base_salary == 'yes' and not self.contract_qualification_id.is_hc:
            amount = self.base_salary
        if base_salary:
            base_salary.montant = amount

    @api.one
    def check_incomplete_month(self, slip_start, slip_end):
        input_base_salary = self.rubric_ids.filtered(
            lambda r: r.rubric_conf == self.env.ref('hr_copefrito_paie.RUBRIC_100')).montant
        rubric_dics = {}
        for rub in self.rubric_ids:
            rubric_dics[rub.rubric_conf.id] = rub.montant
        nb_hours = self.monthly_hours_amount_id.hours
        nb_days_start = self.get_number_days(self.date_start)  # sum of days in a month
        date_start_date = datetime.strptime(self.date_start, "%Y-%m-%d")
        slip_date_start = datetime.strptime(slip_start, "%Y-%m-%d")
        slip_date_end = datetime.strptime(slip_end, "%Y-%m-%d")
        is_incomplete = False
        # is_starting = date_start_date.month == slip_date_start.month and date_start_date.year == slip_date_start.year
        is_starting = date_start_date.month == slip_date_end.month and date_start_date.year == slip_date_end.year
        starte_a_month_before = date_start_date.month < slip_date_end.month and date_start_date.year == slip_date_end.year and date_start_date.month == slip_date_start.month
        is_ending = False
        start_incomplete = False
        end_incomplete = False

        diff_date = lambda d1, d2: (datetime.strptime(str(d2), "%Y-%m-%d") - (
            datetime.strptime(str(d1), "%Y-%m-%d"))).days

        if self.date_end:
            date_end_date = datetime.strptime(self.date_end, "%Y-%m-%d")
            is_ending = date_end_date and date_end_date.month == slip_date_end.month and date_end_date.year == slip_date_end.year

        day_left = 0
        # if is_starting and date_start_date > slip_date_start:
        if (is_starting and date_start_date.day > 1) or (
                starte_a_month_before and date_start_date.day > slip_date_start.day):
            rf_date_start = self.date_start
            rf_date_end = slip_end
            start_incomplete = True
            is_incomplete = True
            # day_left += diff_date(slip_start, self.date_start)
            day_left += date_start_date.day - 1

        # if is_ending and date_end_date < slip_date_end:
        if is_ending and date_end_date.day < 30:
            rf_date_start = slip_start
            rf_date_end = self.date_end
            end_incomplete = True
            is_incomplete = True
            # day_left += diff_date(self.date_end, slip_end)
            day_left += 30 - date_end_date.day

        # check if the employee doesn't finish a month
        if start_incomplete and end_incomplete:
            rf_date_start = self.date_start
            rf_date_end = self.date_end

        if is_incomplete:
            # nb_dayoff = self.env['training.holiday.period'].get_nb_days(rf_date_start, rf_date_end)
            # coefficient = float(diff_date(rf_date_start, rf_date_end)) / float(diff_date(slip_start, slip_end))
            coefficient = float(30 - day_left) / 30
            for rub_key in rubric_dics.keys():
                rubric_dics[rub_key] *= coefficient
                rubric_dics["qty_" + str(rub_key)] = coefficient * nb_hours

        return is_incomplete, rubric_dics

    @api.multi
    def refresh_base_salary(self):
        for contract in self:
            contract.indice = contract.contract_qualification_id.indice if contract.seniority_year < contract.contract_qualification_id.indice_duration or contract.contract_qualification_id.indice_duration == 0 else contract.contract_qualification_id.indice_seniority
            contract._compute_point_indice()
            base_salary = contract.rubric_ids.filtered(
                lambda c: c.rubric_conf.id == self.env.ref('hr_copefrito_paie.RUBRIC_100').id)
            if contract.employee_id.company_id.compute_base_salary == 'yes' and base_salary and not contract.contract_qualification_id.is_hc:
                input_base_salary = contract.base_salary
                # nb_hours = contract.monthly_hours_amount_id.hours
                # nb_days = self.get_number_days(self.date_start)
                # date_start_date = datetime.strptime(contract.date_start, "%Y-%m-%d")
                # today_date = datetime.strptime(fields.Datetime.now(), "%Y-%m-%d %H:%M:%S")
                # nb_day_first_month = nb_days - date_start_date.day + 1
                #
                # # get all dayoffs in the month when the employee starts to work
                # dayoff = self.env['training.holiday.period'].search(
                #     [('date_start', '>=', contract.date_start),
                #      ('date_stop', '<=', "%s-%s-%s" % (date_start_date.year, date_start_date.month, nb_days))])
                # diff_date = lambda d1, d2: (datetime.strptime(str(d2), "%Y-%m-%d") - (
                #     datetime.strptime(str(d1), "%Y-%m-%d"))).days + 1
                # nb_dayoff = sum([diff_date(d.date_start, d.date_stop) for d in dayoff])
                #
                # """
                #     check if today's month is the same as the month of date_start in the contract
                #     check if the employee doesn't start to work on the first day of the month
                #     if so: the basic salary should be recomputed
                # """
                # if date_start_date.month == today_date.month and date_start_date.day > 1:
                #     input_base_salary *= float((nb_day_first_month) - nb_dayoff) * 8 / nb_hours
                base_salary.montant = input_base_salary

    @api.multi
    def update_base_salary(self):
        for contract in self:
            base_salary = contract.rubric_ids.filtered(
                lambda c: c.rubric_conf.id == self.env.ref('hr_copefrito_paie.RUBRIC_100').id)
            if contract.employee_id.company_id.compute_base_salary == 'yes' and base_salary and not contract.contract_qualification_id.is_hc:
                base_salary.montant = contract.base_salary

    @api.model
    def get_number_days(self, str_date):
        conv_date = datetime.strptime(str_date, "%Y-%m-%d")
        return monthrange(conv_date.year, conv_date.month)[1]

    # @api.one
    # @api.depends('employee_id')
    # def compute_base_salary_auto(self):
    #     self.base_salary_auto = self.employee_id.company_id.compute_base_salary == 'yes'

    @api.multi
    @api.depends('working_hours')
    def _calculate_weekly_hours(self):  ##-
        """
        Compute hours consumed of a week in contract type
        """
        for rec in self:
            if rec.working_hours.attendance_ids:
                self.env.cr.execute(
                    "select sum(to_char(to_timestamp((hour_to) * 60) - to_timestamp((hour_from) * 60),'MI')::float) from resource_calendar_attendance where calendar_id = '" + str(
                        rec.working_hours.id) + "'")
                rec.weekly_hours = self.env.cr.fetchone()[0]
            else:
                rec.weekly_hours = 0

    @api.multi
    @api.depends('weekly_hours')
    def _calculate_monthly_hours(self):  ##-
        """
        Compute hours consumed of one month in contract type
        """
        for rec in self:
            rec.monthly_hours = rec.weekly_hours * 4

    @api.one
    @api.depends('date_start', 'date_end', 'trial_date_start')
    def _compute_seniority(self):
        current_date = time.strftime("%Y-%m-%d")
        now = datetime.today()
        ref_date = False
        seniority = False
        to_date = lambda d: datetime.strptime(str(d), "%Y-%m-%d")
        if self.trial_date_start:
            ref_date = self.trial_date_start
        else:
            ref_date = self.date_start
        ref_date_obj = datetime.strptime(ref_date, '%Y-%m-%d').date()
        if self.date_end > current_date or not self.date_end:
            self.seniority = (to_date(current_date) - to_date(ref_date)).days + 1
            seniority = relativedelta(now, ref_date_obj) + relativedelta(days=+1)
        else:
            self.seniority = (to_date(self.date_end) - to_date(ref_date)).days + 1
            date_en_obj = to_date(self.date_end).date()
            date_start_obj = to_date(self.date_start).date()
            seniority = relativedelta(date_en_obj, date_start_obj) + relativedelta(days=+1)
        self.seniority_year = seniority.years
        self.seniority_month = seniority.months
        year = str(seniority.years) + ' ans ' if seniority.years > 0 else ''
        month = str(seniority.months) + ' mois ' if seniority.months > 0 else ''
        day = str(seniority.days) + ' jours' if seniority.days > 0 else ''
        self.seniority_char = year + month + day

    @api.one
    @api.onchange('code_service')
    def _onchange_code_service(self):
        self.department_id = self.code_service.service_id
        if not (self.department_id.id == self.job_id.service_id.id):
            self.code_poste = False
            self.job_id = False

    @api.one
    @api.onchange('code_poste')
    def _onchange_code_poste(self):
        if self.code_poste:
            self.job_id = self.code_poste.job_id
            self.department_id = self.code_poste.job_id.service_id

    @api.one
    @api.onchange('job_id')
    def _onchange_poste(self):
        if self.job_id:
            self.code_poste = self.job_id.code
            self.department_id = self.job_id.service_id

    @api.one
    @api.onchange('department_id')
    def _onchange_department_id(self):
        self.code_service = self.department_id.code

    @api.onchange('code_service', 'department_id')
    def dynamic_domain(self):
        if self.code_service or self.department_id:
            return {'domain': {'job_id': [('service_id.id', '=', "%s" % self.department_id.id)],
                               'code_poste': [('job_id.service_id.id', '=', "%s" % self.department_id.id)]}}

    @api.one
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.monthly_hours_amount_id = self.employee_id.company_id.monthly_hours_amount_id

    @api.one
    @api.onchange('monthly_hours_amount_id')
    def _compute_point_indice(self):
        current_date = time.strftime("%Y-%m-%d")
        val = float("inf")
        pi_env = self.env['point.indice'].search([('effective_date', '<=', current_date)])
        if pi_env:
            res = False
            for pi in pi_env:
                diff = (datetime.strptime(str(current_date), "%Y-%m-%d") - (
                    datetime.strptime(str(pi.effective_date), "%Y-%m-%d"))).days
                if val > diff:
                    val = diff
                    res = pi.id
            pi_model = self.env['point.indice']
            old_pi = self.point_indice
            old_pi_value, old_pi_date = False, False
            if old_pi:
                old_pi_value = str(self.point_indice.amount)
                old_pi_date = pi_model.convert_date_to_french_string(self.point_indice.effective_date)
            self.point_indice = self.env['point.indice'].browse([res])
            new_pi_value = str(self.point_indice.amount)
            new_pi_date = pi_model.convert_date_to_french_string(self.point_indice.effective_date)
            self.point_indice_history(new_pi_date, new_pi_value, old_pi, old_pi_value, old_pi_date)
        else:
            self.point_indice = False

    @api.model
    def point_indice_history(self, new_pi_date, new_pi_value, old_pi=False, old_pi_value=False, old_pi_date=False):
        body_html = "<p>Le point d'indice a changé:<ul>"
        if old_pi:
            body_html += "<li>Date de prise d'effet: %s &rarr; %s</li>" % (old_pi_date, new_pi_date)
            body_html += "<li>Valeur de point d'indice: %s &rarr; %s</li>" % (old_pi_value, new_pi_value)
        else:
            body_html += "<li>Date de prise d'effet: %s</li>" % (new_pi_date)
            body_html += "<li>Valeur de point d'indice: %s</li>" % (new_pi_value)
        body_html += "</ul></p>"
        self.message_post(body=body_html, subtype='mail.mt_note')

    @api.model
    def set_hidden_point_indice(self):
        current_date = time.strftime("%Y-%m-%d")
        pi_model = self.env['point.indice']
        pi_env = pi_model.search([('effective_date', '<=', current_date)])
        contract_ids = self.search([])
        if pi_env:
            for contract in contract_ids:
                val = float("inf")
                res = False
                for pi in pi_env:
                    diff = (datetime.strptime(str(current_date), "%Y-%m-%d") - (
                        datetime.strptime(str(pi.effective_date), "%Y-%m-%d"))).days
                    if val > diff:
                        val = diff
                        res = pi.id
                if res and res != contract.hidden_point_indice.id:
                    rec = self.env['point.indice'].browse([res])
                    old_pi = contract.hidden_point_indice
                    if old_pi:
                        old_pi_value = str(contract.hidden_point_indice.amount)
                        old_pi_date = pi_model.convert_date_to_french_string(
                            contract.hidden_point_indice.effective_date)
                    contract.hidden_point_indice = self.env['point.indice'].browse([res])
                    new_pi_value = str(contract.hidden_point_indice.amount)
                    new_pi_date = pi_model.convert_date_to_french_string(contract.hidden_point_indice.effective_date)
                    body_html = "<p>Le point d'indice a changé:<ul>"
                    if old_pi:
                        body_html += "<li>Date de prise d'effet: %s &rarr; %s</li>" % (old_pi_date, new_pi_date)
                        body_html += "<li>Valeur de point d'indice: %s &rarr; %s</li>" % (old_pi_value, new_pi_value)
                    else:
                        body_html += "<li>Date de prise d'effet: %s</li>" % (new_pi_date)
                        body_html += "<li>Valeur de point d'indice: %s</li>" % (new_pi_value)
                    body_html += "</ul></p>"
                    contract.message_post(body=body_html, subtype='mail.mt_note')
                else:
                    print
                    "Pas de mise à jour"

    @api.one
    @api.depends('employee_id', 'point_indice', 'indice', 'monthly_hours_amount_id')
    def _compute_base_salary(self):
        self.base_salary = round(round(self.point_indice_val * self.indice, 2) * self.monthly_hours_amount_id.hours)

    def _track_subtype(self, init_values):
        result = super(hr_contract, self)._track_subtype(init_values)
        current_date = time.strftime("%Y-%m-%d")
        if self.state == 'pending' or self.state == 'close':
            return result
        elif self.trial_date_end < current_date:
            return 'hr_copefrito_paie.mt_contract_trial_date_end'
        return False

    @api.one
    @api.depends('trial_date_end')
    def _compute_trial_is_end(self):
        # current_date = time.strftime("%Y-%m-%d")
        current_date = (datetime.now() + timedelta(16)).strftime("%Y-%m-%d")
        if self.id:
            if self.trial_date_end and self.trial_date_end < current_date:
                if not self.trial_is_end:
                    self.send_mail(self.id, 'hr_copefrito_paie.email_template_notification_trial_expired')
                self.trial_is_end = True
            else:
                self.trial_is_end = False

    @api.one
    @api.depends('renew_trial_date_end')
    def _compute_renew_trial_is_end(self):
        # current_date = time.strftime("%Y-%m-%d")
        current_date = (datetime.now() + timedelta(16)).strftime("%Y-%m-%d")
        if self.id:
            if self.renew_trial_date_end and self.renew_trial_date_end < current_date:
                if not self.renew_trial_is_end:
                    self.send_mail(self.id, 'hr_copefrito_paie.email_template_notification_renew_trial_expired')
                self.renew_trial_is_end = True
            else:
                self.renew_trial_is_end = False

    @api.one
    @api.depends('allaitement_date_end')
    def _compute_allaitement_is_end(self):
        current_date = time.strftime("%Y-%m-%d")
        if self.id:
            if self.allaitement_date_end and self.allaitement_date_end < current_date:
                if not self.allaitement_is_end:
                    self.send_mail(self.id, 'hr_copefrito_paie.email_template_notification_allaitement_expired')
                self.allaitement_is_end = True
            else:
                self.allaitement_is_end = False

    @api.model
    def send_mail(self, contract_id, email_template, auto_commit=True):
        mail_mail_obj = self.env['mail.mail']
        template = self.env.ref(email_template)
        values = template.with_context().generate_email(contract_id)
        values['email_from'] = self.env.user.company_id.email
        pay_manager_group = self.env.ref('hr_copefrito_paie.group_pay_manager')
        recipient_ids = []
        for pay_manager in pay_manager_group.users:
            if self.browse(contract_id).employee_id.company_id.id in pay_manager.company_ids.ids:
                recipient_ids.append((4, pay_manager.partner_id.id))
        values['recipient_ids'] = recipient_ids
        msg_id = mail_mail_obj.create(values)
        msg_id.send()
        mail_thread = self.env['mail.thread']
        mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'],
                                 partner_ids=recipient_ids)

    @api.constrains('renew_trial_date_start', 'trial_date_end')
    def _constrains_renew_trial_date_start(self):
        if self.renew_trial_date_start and self.renew_trial_date_start <= self.trial_date_end:
            raise ValidationError(
                'La date début de renouvellement de période d\'essai doit être supérieur à la date de fin de période d\'essai')

    @api.constrains('allaitement_date_start', 'allaitement_date_end')
    def _constrains_allaitement_date(self):
        if self.allaitement_date_start > self.allaitement_date_end:
            raise ValidationError('La date début d\'allaitement doit être inférieur à la date de fin d\'allaitement')

    @api.onchange('allaitement')
    def _onchange_allaitement(self):
        if not self.allaitement:
            self.allaitement_date_start = False
            self.allaitement_date_end = False

    @api.onchange('to_renew')
    def _onchange_to_renew(self):
        if not self.to_renew:
            self.renew_trial_duration = 0
            self.renew_trial_date_start = False

    @api.one
    def _get_current_url(self):
        context = self._context
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        params = context.get('params', False)
        fragment = dict()
        base = '/web#'
        if params:
            fragment['id'] = self.id
            fragment['view_type'] = 'form'
            fragment['model'] = 'hr.contract'
        self.current_url = urljoin(base_url, base + werkzeug.url_encode(fragment))

    @api.one
    def _get_cancel_url(self):
        context = self._context
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        params = context.get('params', False)
        fragment = dict()
        base = '/web#'
        if params:
            fragment['id'] = self.id
            fragment['view_type'] = 'form'
            fragment['model'] = 'hr.contract'
        self.cancel_url = urljoin(base_url, base + werkzeug.url_encode(fragment)) + '/disable/' + str(self.id)

    @api.onchange('trial_date_start')
    def _onchange_date_start(self):
        if self.trial_date_start:
            self.date_start = self.trial_date_start

    payslip_payment_mode_id = fields.Many2one('hr.payslip.payment.mode', string=u'Mode de paiement', store=True,
                                              related='employee_id.payment_mode')
    contract_qualification_id = fields.Many2one('hr.contract.qualification', string=u"Catégorie Professionnelle")
    type_salaire = fields.Selection([('brut', 'BRUT'), ('net', 'NET')], string=u'Type salaire', required=True,
                                    default='brut')
    org_sante_id = fields.Many2one('res.organisme.medical', string=u"Organisme Médicale")
    computed_state = fields.Selection(
        [('draft', 'Brouillon'), ('instance', 'Instance'), ('open', 'Essai'), ('renewed', 'Essai renouvelé'),
         ('pending', 'A Renouveler'), ('active', 'Confirmé'), ('close', 'Fin')],
        string=u'Status', track_visibility='onchange', compute="compute_state",
        help='Status of the contract')
    weekly_hours = fields.Integer(compute='_calculate_weekly_hours',
                                  string=u'Heures hebdomadaires',
                                  help=u'Nombre d\'heures total dans la semaine',
                                  readonly=True)
    monthly_hours = fields.Integer(compute='_calculate_monthly_hours',
                                   string=u'Heures mensuelles',
                                   help=u'Nombre d\'heures total dans un mois',
                                   readonly=True)
    monthly_hours_amount_id = fields.Many2one('monthly.hours.contract.data', string=u'Volume horaire mensuelle')  ##-
    work_night = fields.Boolean(u'Travail de nuit')  ##-
    trial_duration = fields.Integer(u'Durée période d\'essai')
    renew_trial_duration = fields.Integer(u'Renouvellement essai')
    trial_date_end = fields.Date('Trial End Date', compute="_compute_trial_date_end", readonly=True, store=True)
    status = fields.Selection([('permanent', 'Permanent'), ('journalier', 'Journalier'), ('stagiaire', 'Stagiaire'),
                               ('visiteur', 'Visiteur')], string=u'Statut', default='permanent')
    allaitement = fields.Boolean(string=u"Allaitement")
    allaitement_date_start = fields.Date(string=u"Date début allaitement")
    allaitement_date_end = fields.Date(string=u"Date fin allaitement")
    allaitement_is_end = fields.Boolean(u'Date d\'allaitement expiré', compute='_compute_allaitement_is_end',
                                        default=False, store=True)
    code_poste = fields.Many2one('hr.code.poste', u'Code poste', required=True)
    code_service = fields.Many2one('hr.code.service', u'Code service', required=True)
    num_contract = fields.Char(string=u"N° Contrat", required=False)
    hol_per_month = fields.Float(string=u"Nombre de congés par mois", related='job_id.hol_per_month', readonly=True)
    seniority = fields.Integer(string=u"Ancienneté", compute=_compute_seniority)
    seniority_char = fields.Char(string=u"Ancienneté", compute=_compute_seniority)
    seniority_year = fields.Integer(string=u"Année", compute=_compute_seniority)
    seniority_month = fields.Integer(string=u"Année", compute=_compute_seniority)
    rubric_ids = fields.One2many("hr.contract.rubric", "contract_id", string=u"Rubriques")
    indice_start = fields.Integer(string=u"Indice à l'embauche", related="contract_qualification_id.indice",
                                  readonly=True)
    indice_seniority = fields.Integer(string=u"Indice d'ancienneté",
                                      related="contract_qualification_id.indice_seniority", readonly=True)
    indice_duration = fields.Integer(string=u"Durée de changement d'indice",
                                     related="contract_qualification_id.indice_duration", readonly=True)
    indice = fields.Integer(string=u"Indice utilisé", compute="compute_indice", readonly=True, store=True)
    point_indice = fields.Many2one('point.indice', string=u"Point d\'indice")
    alert_indice = fields.Selection(
        [('no_alert', 'Sans alerte'), ('one_month_left', '1 mois'), ('need_refresh', 'A actualiser')],
        string=u"Alerte indice", compute="compute_alert")
    hidden_point_indice = fields.Many2one('point.indice', string=u"Indice")
    point_indice_val = fields.Float(string=u"Valeur du point d\'indice", related='point_indice.amount', readonly=True)
    base_salary = fields.Float(string=u"Salaire minimum", compute=_compute_base_salary)
    type_id = fields.Many2one('hr.contract.type', string=u"Code contrat", default=False, required=False)
    hierar_level = fields.Selection([('one', 'I'), ('two', 'II')], string=u"Niveau hierarchique")
    additional_hour = fields.Boolean(u'Heure supplémentaire')
    trial_is_end = fields.Boolean(u'Période d\'essai expiré', compute='_compute_trial_is_end', default=False,
                                  store=True)
    renew_trial_date_start = fields.Date(u'Date début renouvellement période d\'essai')
    renew_trial_date_end = fields.Date(u'Date fin renouvellement période d\'essai',
                                       compute="_compute_renew_trial_date_end", store=True)
    renew_trial_is_end = fields.Boolean(u'Renouvellement Période d\'essai expiré',
                                        compute='_compute_renew_trial_is_end',
                                        default=False,
                                        store=True)
    name = fields.Char('Contract Reference', required=False)
    department_id = fields.Many2one('hr.department', string=u'Service')
    struct_id = fields.Many2one('hr.payroll.structure', default=lambda self: self.env.ref(
        'hr_copefrito_paie.hr_payroll_structure_structure_cdi_r0'))
    matricule = fields.Char("Matricule", related="employee_id.identification_cdi_id", readonly=True, store=True)
    current_url = fields.Char(string=u"URL", compute='_get_current_url')
    to_renew = fields.Boolean(string=u"A renouveler")
    contract_model = fields.Many2one('hr.contract.model', string=u"Modèle de contrat")
    visa_deliver = fields.Date(string=u"Date de délivrance Visa")
    permit_deliver = fields.Date(string=u"Date de délivrance permis")
    permit_expire = fields.Date(string=u"Date d'expiration permis")

    state = fields.Selection(string=u"Etat du contrat",
                             selection=[('draft', 'Brouillon'), ('instance', 'Instance'), ('open', 'Essai'),
                                        ('renewed', 'Essai renouvelé'), ('active', 'Actif'), ('close', 'Fin')],
                             default='draft', help='Status of the contract')
    is_hc = fields.Boolean(related="contract_qualification_id.is_hc")

    variable_rubric_ids = fields.Many2many('hr.payslip.rubric.config', "hr_payslip_rubric_hr_contract_rel",
                                           "contract_id", "rub_id",
                                           string=u"Rubriques variables")
    total_fix_salary = fields.Float('Salaire sur contract fixe', compute='compute_total_fix_salary')
    enable_notifications = fields.Boolean(string="Activer l'envoi de notifications", default=True)
    cancel_url = fields.Char(string=u"URL", compute='_get_cancel_url')

    @api.one
    @api.depends('rubric_ids')
    def compute_total_fix_salary(self):
        self.total_fix_salary = sum(self.rubric_ids.mapped('montant'))

    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = super(hr_contract, self).onchange_employee_id(cr, uid, ids, employee_id, context)
        if employee_id:
            emp_obj = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            monthly_hours_amount_id = emp_obj.company_id.monthly_hours_amount_id
            res['value']['monthly_hours_amount_id'] = monthly_hours_amount_id.id
        return res

    @api.one
    @api.depends('trial_duration', 'trial_date_start')
    def _compute_trial_date_end(self):  ##-
        """
        Compute trial date end depending trial/renew
        duration and trial date start
        """
        if self.trial_date_start: self.trial_date_end = (
                datetime.strptime(str(self.trial_date_start), "%Y-%m-%d") + relativedelta(
            months=+self.trial_duration)).strftime('%Y-%m-%d')

    @api.one
    @api.depends('renew_trial_duration', 'renew_trial_date_start')
    def _compute_renew_trial_date_end(self):  ##-
        """
        Compute renew trial date end depending renew
        duration and trial date start
        """
        if self.renew_trial_date_start: self.renew_trial_date_end = (
                datetime.strptime(str(self.renew_trial_date_start), "%Y-%m-%d") + relativedelta(
            months=+self.renew_trial_duration)).strftime('%Y-%m-%d')

    @api.multi
    @api.depends('num_contract', 'name')
    def name_get(self):
        result = []
        context = self._context
        for contract in self:
            if contract.name:
                val = contract.num_contract + " - " + contract.name
            else:
                val = contract.num_contract
            if context.get('from_rubric_conf') and contract.matricule:
                val += " - " + contract.matricule
            result.append((contract.id, val))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(hr_contract, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('matricule', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    @api.one
    @api.depends('contract_qualification_id')
    def compute_indice(self):
        self.indice = self.contract_qualification_id.indice

    @api.one
    @api.depends('contract_qualification_id', 'seniority_year')
    def compute_alert(self):
        alert = 'no_alert'
        if self.contract_qualification_id.indice_duration > 0:
            if self.indice != self.contract_qualification_id.indice_seniority and self.seniority_year >= self.contract_qualification_id.indice_duration:
                alert = 'need_refresh'
            elif self.seniority_year < self.contract_qualification_id.indice_duration:
                if self.seniority_month >= 11 and self.seniority_year == self.contract_qualification_id.indice_duration - 1:
                    alert = 'one_month_left'
                if self.indice != self.contract_qualification_id.indice:
                    alert = 'need_refresh'
        elif self.indice != self.contract_qualification_id.indice and self.contract_qualification_id.indice_duration == 0:
            alert = 'need_refresh'
        self.alert_indice = alert

    @api.multi
    def make_instance(self):
        self.state = 'instance'

    @api.multi
    def make_trial(self):
        self.state = 'open'

    @api.multi
    def make_active(self):
        self.state = 'active'

    @api.multi
    def make_renewed(self):
        self.write({
            'state': 'renewed',
            'to_renew': True
        })

    @api.multi
    def make_closed(self):
        for rec in self:
            if not rec.date_end:
                raise UserError('Vous devez spécifier la date de débauche.')
            else:
                rec.write({
                    'state': 'close'
                })

    @api.multi
    def make_draft(self):
        self.write({'state': 'draft'})

    @api.one
    @api.depends('state')
    def compute_state(self):
        state = self.state
        # current_date = time.strftime("%Y-%m-%d")
        current_date = (datetime.now() + timedelta(16)).strftime("%Y-%m-%d")
        trial_expired = self.trial_date_end < current_date and self.state == 'open'
        renew_trial_expired = self.to_renew and self.renew_trial_date_end < current_date and self.state == 'renewed'
        if trial_expired or renew_trial_expired:
            state = 'pending'
        self.computed_state = state

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(hr_contract, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if view_type == 'form':
            employe_has_contract_ids = self.search([('state', '!=', 'close')]).mapped('employee_id').ids
            domain = "[('id', 'not in', %s)]" % employe_has_contract_ids
            for node in doc.xpath("//field[@name='employee_id']"):
                node.set('domain', domain)
        elif view_type == 'tree' and self._context.get('from_oe_stat_button'):
            active_id = self._context['search_default_employee_id']
            has_contract = self.env['hr.employee'].browse(active_id).contract_ids.filtered(lambda c: c.state != 'close')
            if has_contract:
                for node in doc.xpath("//tree"):
                    node.set('create', 'false')
        result['arch'] = etree.tostring(doc)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super(hr_contract, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                  lazy=lazy)
        return res


class HrContractRubric(models.Model):
    _name = 'hr.contract.rubric'

    rubric_conf = fields.Many2one("hr.payslip.rubric.config", "Rubrique")
    rubric_conf_name = fields.Char("Rubrique", related="rubric_conf.name")
    montant = fields.Float("Montant", digits=dp.get_precision('Montant général'))
    contract_id = fields.Many2one("hr.contract", "Contract")
    code = fields.Char("Code", related="rubric_conf.code")
    base_salary_auto = fields.Boolean(string=u"Calcul automatique salaire de base", compute="compute_base_salary_auto")
    is_hc = fields.Boolean(related="contract_id.contract_qualification_id.is_hc")
    hc_indice = fields.Integer(related="contract_id.contract_qualification_id.indice")
    active = fields.Boolean(string="active", default=True)

    @api.multi
    def write(self, vals):
        old_values = {}
        for contract_rub in self:
            if vals.has_key('montant'):
                old_montant = contract_rub.montant
                old_values[contract_rub.id] = {"montant": old_montant}
        res = super(HrContractRubric, self).write(vals)
        for contract_rub in self:
            if vals.has_key('montant'):
                MailTemplate = self.env['mail.template']
                rubric_name = contract_rub.rubric_conf.name.encode("utf-8")
                body_html = "<p>Rubrique <strong>" + rubric_name + "</strong> modifiée<ul>"
                if vals.has_key('montant'):
                    body_html += "<li>Montant: " + str(old_values.get(contract_rub.id)["montant"]) + " &rarr; " + str(
                        contract_rub.montant) + "</li>"
                body_html += "</ul></p>"
                notif = MailTemplate.render_template(body_html, 'hr.contract.rubric', contract_rub.id)
                contract_rub.contract_id.message_post(body=notif, subtype='mail.mt_note')
        return res

    @api.one
    @api.depends('contract_id')
    def compute_base_salary_auto(self):
        self.base_salary_auto = self.contract_id.employee_id.company_id.compute_base_salary == 'yes'
