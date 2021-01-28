# -*- coding: utf-8 -*-
import logging

from openerp import models, api, fields
from openerp.osv import osv
from openerp.netsvc import logging

_logger = logging.getLogger(__name__)

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError, ValidationError
from lxml import etree


class hr_payslip_run(models.Model):
    _inherit = 'hr.payslip.run'

    @api.returns('self')
    def _default_stage(self):
        return self.env['hr.payslip.state'].search([], limit=1)

    company_id = fields.Many2one('res.company', string=u'Société', required=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.account'))
    class_ids = fields.One2many("hr.payslip.class", "payslip_run", u"Classes")
    date_payement = fields.Date('Date de paiement')
    total_payslip = fields.Integer(u'Total de bulletin de paie', compute='_compute_total_payslip')
    responsable_employee_id = fields.Many2one('hr.employee', string=u"Employé responsable")
    responsable = fields.Many2one('res.users', string=u"Responsable", compute="compute_responsable_employee_id",
                                  store=True, readonly=True)
    total_draft = fields.Integer(u'Total de bulletin à l\'état brouillon')
    #    kanban_state = fields.Selection([('normal', 'Brouillon'), ('blocked', 'En attente'), ('done', 'Validé'), ('pending', 'Instance')],
    #                                    string=u'Kanban State', required=False, default='normal', track_visibility='onchange')
    #    stage_id = fields.Many2one('hr.payslip.state', string=u'Stage', track_visibility='onchange', default=_default_stage)
    nb_classes = fields.Integer(u'Nombre de classes', compute='_compute_nb_classes')
    nb_classes_draft = fields.Integer(u'Nombre de classes brouillons', compute='_compute_nb_classes')
    nb_classes_pending = fields.Integer(u'Nombre de classes en cours', compute='_compute_nb_classes')
    nb_classes_instance = fields.Integer(u'Nombre de classes en instances', compute='_compute_nb_classes')
    nb_classes_validate = fields.Integer(u'Nombre de classes validées', compute='_compute_nb_classes')
    nb_classes_closed = fields.Integer(u'Nombre de classes clôturées', compute='_compute_nb_classes')

    nb_slip_ids = fields.Integer(u'Nombre de bulletins', compute='_compute_nb_slip_ids')
    nb_slip_ids_draft = fields.Integer(u'Nombre de bulletins brouillons', compute='_compute_nb_slip_ids')
    nb_slip_ids_verify = fields.Integer(u'Nombre de bulletins en cours', compute='_compute_nb_slip_ids')
    nb_slip_ids_instance = fields.Integer(u'Nombre de bulletins instances', compute='_compute_nb_slip_ids')
    nb_slip_ids_validate = fields.Integer(u'Nombre de bulletins validées', compute='_compute_nb_slip_ids')
    nb_slip_ids_waiting = fields.Integer(u'Nombre de bulletins en attente de déclaration',
                                         compute='_compute_nb_slip_ids')
    nb_slip_ids_done = fields.Integer(u'Nombre de bulletins terminés', compute='_compute_nb_slip_ids')
    nb_slip_ids_cancel = fields.Integer(u'Nombre de bulletins annulés', compute='_compute_nb_slip_ids')
    state = fields.Selection(
        [('draft', 'Brouillon'), ('pending', 'En cours'), ('instance', 'Instance'), ('validate', u'Validé'),
         ('waiting', u'En attente de déclaration'), ('close', u'Clôturé')], 'Etat', default='draft',
        compute='_compute_nb_classes', store=True)
    mail_is_sent = fields.Boolean(default=False)
    is_waiting = fields.Boolean(default=False)
    button_draft_visibility = fields.Boolean(compute='compute_button_draft_visibility')
    active = fields.Boolean(string=u"Active", default=True)
    is_verified = fields.Boolean(compute='compute_is_verified')
    around_value = fields.Integer(u'Valeur arrondie')
    alert_signature = fields.Boolean(u'Alerte signature', default=False, compute='_compute_nb_classes', store=True)
    ajusted_register = fields.Char(string="matricule normalisé", compute='get_ajusted_register')
    computed_payslips = fields.Boolean(string='Already computed period', default=False)

    @api.multi
    def invalidate(self):
        for run in self:
            for c in run.class_ids.filtered(lambda c: c.state != 'neutre'):
                for rub in c.rubric_ids.filtered(lambda r: r.state != 'neutre'):
                    rub.make_draft()
        self.write({'state': 'draft'})
        for c in self.class_ids:
            for rub in c.rubric_ids:
                for input_id in rub.input_ids:
                    input_id.color_button = "grey"
                    input_id.is_readonly = False
        self.computed_payslips = False

    @api.one
    @api.depends('class_ids.state')
    def _compute_nb_classes(self):
        try:
            self.ensure_one()
            self.nb_classes = len(self.class_ids)
            self.nb_classes_draft = len(self.class_ids.filtered(lambda c: c.state == 'draft'))
            self.nb_classes_pending = len(self.class_ids.filtered(lambda c: c.state == 'pending'))
            self.nb_classes_instance = len(self.class_ids.filtered(lambda c: c.state == 'instance'))
            self.nb_classes_validate = len(self.class_ids.filtered(lambda c: c.state == 'validate'))
            self.nb_classes_closed = len(self.class_ids.filtered(lambda c: c.state == 'closed'))

            if self.class_ids and self.ids:
                # all class_ids is in draft
                if (all(st.state == 'draft' for st in self.class_ids)):
                    self.state = 'draft'
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET state = %s where id = %s
                    """, ('draft', self.id))
                    self.mail_is_sent = False
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                    """, (False, self.id))

                # at least one rubric is in pending
                elif (any(st.state == 'pending' for st in self.class_ids)):
                    self.state = 'pending'
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET state = %s where id = %s
                    """, ('pending', self.id))
                    self.mail_is_sent = False
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                    """, (False, self.id))

                # at least one rubric is in instance and there is no rubric in draft or pending
                elif (any(st.state == 'instance' for st in self.class_ids) and not (
                        any(st.state == 'draft' or st.state == 'pending' for st in self.class_ids))):
                    self.state = 'instance'
                    self.mail_is_sent = False
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s""", (False, self.id))

                    # update the state of payslip linked to the payslip_run
                    for payslip_id in self.slip_ids:
                        if payslip_id.state not in ['instance', 'validate', 'waiting', 'done', 'cancel']:
                            payslip_id.state = 'instance'
                            self._cr.execute("""
                                UPDATE hr_payslip SET state = %s where payslip_run_id = %s and id = %s""",
                                             ('instance', self.id, payslip_id.id))

                # all class_ids is validate or neutre
                elif (all(st.state == 'validate' or st.state == 'neutre' for st in self.class_ids)):
                    if not self.responsable.signature_img:
                        self.alert_signature = True
                        self._cr.execute("""
                            UPDATE hr_payslip_run SET alert_signature = %s where id = %s
                        """, (True, self.id))
                        self.state = 'instance'
                        self._cr.execute("""
                            UPDATE hr_payslip_run SET state = %s where id = %s
                        """, ('instance', self.id))
                    else:
                        self.alert_signature = False
                        self._cr.execute("""
                            UPDATE hr_payslip_run SET alert_signature = %s where id = %s
                        """, (False, self.id))
                        if self.is_waiting:
                            self.state = 'waiting'
                            self._cr.execute("""
                                UPDATE hr_payslip_run SET state = %s where id = %s
                            """, ('waiting', self.id))
                        else:
                            self.state = 'validate'
                            self._cr.execute("""
                                UPDATE hr_payslip_run SET state = %s where id = %s
                            """, ('validate', self.id))
                        # self.write({'state': 'validate'})
                        #                 if not self.mail_is_sent:
                        #                     mail_mail_obj = self.env['mail.mail']
                        #                     template = self.env.ref('hr_copefrito_paie.email_template_notification_payslip_run_validate')
                        #                     values = template.with_context().generate_email(self.id)
                        #                     values['email_from'] = self.env.user.company_id.email
                        #                     responsable_paie = self.env.ref('hr_copefrito_paie.group_pay_manager')
                        #                     recipient_ids = [(4, recp_id.partner_id.id) for recp_id in responsable_paie.users]
                        #                     values['recipient_ids'] = recipient_ids
                        #                     msg_id = mail_mail_obj.create(values)
                        #                     #send mail
                        #                     msg_id.send()
                        #                     #odoo notification
                        #                     mail_thread = self.env['mail.thread']
                        #                     mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'], partner_ids= recipient_ids)
                        #                 self.mail_is_sent=True
                        #                 self._cr.execute("""
                        #                     UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                        #                 """, (True, self.id))

                        if not self.computed_payslips:
                            raise ValidationError(_('Please compute the period : %s') % self.name)

                        for payslip_id in self.slip_ids:
                            to_delete = False
                            for line in payslip_id.line_ids:
                                if line.code == 'Salaire de Base' and line.total == 0.0:
                                    to_delete = True
                                    break
                            if to_delete and payslip_id.employee_id.mapped('contract_ids').filtered(
                                    lambda x: x.computed_state == 'active').status == 'journalier':
                                _logger.info('delete payslip %s' % payslip_id)
                                self._cr.execute("""DELETE FROM hr_payslip WHERE id = %s""", (payslip_id.id,))
                        self._cr.commit()

                        sorted_payslip = self.get_sorted_slip_ids()[0]
                        # update the state of payslip linked to the payslip_run
                        # for payslip_id in self.slip_ids:
                        i = 1
                        for payslip_id in self.slip_ids:
                            if payslip_id.state not in ['waiting', 'done', 'cancel']:
                                seq = sorted_payslip[payslip_id.id]
                                number = payslip_id.with_context(from_payslip_run=True).mark_validate()[0] + seq
                                int_seq = int(seq)
                                self._cr.execute("""
                                    UPDATE hr_payslip SET state = %s, number = %s, seq = %s where id = %s
                                """, ('validate', number, int_seq, payslip_id.id))
                                i += 1

                # if all of the classes states are in draft or validate
                elif (all(st.state == 'draft' or st.state == 'neutre' for st in self.class_ids)):
                    self.state = 'draft'
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET state = %s where id = %s
                    """, ('draft', self.id))
                    self.mail_is_sent = False
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                    """, (False, self.id))


                else:
                    self.state = 'pending'
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET state = %s where id = %s
                    """, ('pending', self.id))
                    self.mail_is_sent = False
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                    """, (False, self.id))

                if all(st.state == 'closed' for st in self.class_ids):
                    self.state = 'close'
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET state = %s where id = %s
                    """, ('close', self.id))
                    self.mail_is_sent = True
                    self._cr.execute("""
                        UPDATE hr_payslip_run SET mail_is_sent = %s where id = %s
                    """, (True, self.id))

                    # update the state of payslip linked to the payslip_run
                    #                 for payslip_id in self.slip_ids:
                    #                     if payslip_id.state not in ['done', 'cancel']:
                    #                         payslip_id.state = 'done'
                    #                         self._cr.execute("""
                    #                             UPDATE hr_payslip SET state = %s where payslip_run_id = %s
                    #                         """, ('done', self.id))

            else:
                self.state = 'draft'
        except Exception, e:
            self.env.cr.rollback()
            try:
                if e.name.find(_('Please compute the period : %s') % self.name) >= 0:
                    raise ValidationError(_('Please compute the period : %s') % self.name)
                else:
                    _logger.info("Exception found!")
            except:
                _logger.info("Exception found!")

    # @api.multi
    # def ajusted_register(self):
    #     number_list = []
    #     identification_numbers = self.env['hr.employee'].mapped(lambda e: e.identification_cdi_id)
    #     for number in indentification_numbers:
    #         number.rjust(6, '0')
    #         number_list.append(number)
    #     return number_list

    @api.one
    def get_sorted_slip_ids(self):
        # recs = self.search([], order='create_date desc', limit=1)[0]
        recs = self
        """
            :sorted_payslip : payslip linked to the payslip_run sorted by:
                    1 - CSP (contract_qualification_id.is_hc first
                    2 - Code of the service of the employee
                    3 - Name of the payment mode
                    4 - Matricule of the employee
        """
        # ajusted_register = lambda s: s.rjust(6, '0')
        # sorted_payslip = sorted(recs.slip_ids, key=lambda p: p.employee_id.register)
        # sorted_payslip = sorted(sorted_payslip, key=lambda p: p.payment_mode.name)
        # sorted_payslip = sorted(sorted_payslip, key=lambda p: p.contract_id.department_id.code_service)
        # sorted_payslip = sorted(sorted_payslip, key=lambda p: not p.contract_id.contract_qualification_id.is_hc)

        # fix of useless code above
        sorted_payslip = recs.slip_ids

        res = {}
        # for payslip in sorted_payslip:
        #     print(payslip.employee_id.identification_cdi_id + ' ssssssssssssss ' + payslip.employee_id.register)

        i = 1
        for slip in sorted_payslip:
            res[slip.id] = str(i).rjust(3, '0')
            i += 1
        return res

    @api.one
    @api.depends('slip_ids')
    def _compute_nb_slip_ids(self):
        self.nb_slip_ids = len(self.slip_ids)
        self.nb_slip_ids_draft = len(self.slip_ids.filtered(lambda c: c.state == 'draft'))
        self.nb_slip_ids_verify = len(self.slip_ids.filtered(lambda c: c.state == 'verify'))
        self.nb_slip_ids_instance = len(self.slip_ids.filtered(lambda c: c.state == 'instance'))
        self.nb_slip_ids_validate = len(self.slip_ids.filtered(lambda c: c.state == 'validate'))
        self.nb_slip_ids_waiting = len(self.slip_ids.filtered(lambda c: c.state == 'waiting'))
        self.nb_slip_ids_done = len(self.slip_ids.filtered(lambda c: c.state == 'done'))
        self.nb_slip_ids_cancel = len(self.slip_ids.filtered(lambda c: c.state == 'cancel'))

    @api.multi
    def generate_all(self):
        slip_emp_env = self.env['hr.payslip.employees']
        # take all employee who have an active contract
        # emp_ids = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)], order="id asc").filtered(
        #     lambda e: e.has_active_contract()[0])

        emp_ids = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)], order="id asc").filtered(
            lambda e: self.env['hr.payslip'].get_contract(e, self.date_start, self.date_end))
        context = dict(self._context or {})
        context['active_id'] = self.id

        slip_emp_ids = self.slip_ids.mapped('employee_id') | emp_ids

        # # list of employees already added in the payslip_run
        # for slip in self.slip_ids:
        #     emp_list.append(slip.employee_id.id)
        #
        # # list of employees who don't have a contract
        # for ec in emp_contract:
        #     emp_list.append(ec)
        #
        # for emp in emp_ids:
        #     if emp not in emp_list:
        #         slip_emp_ids.append(emp)

        res = {'employee_ids': [(6, 0, slip_emp_ids.ids)]}
        slip_emp_rec = slip_emp_env.create(res)
        slip_emp_env.browse(slip_emp_rec.id).with_context(context).compute_sheet()

    @api.multi
    @api.depends('slip_ids')
    def _compute_total_payslip(self):
        self.total_payslip = len(self.slip_ids)

    @api.one
    def refresh(self):
        slip_ids = self.slip_ids.filtered(lambda s: s.state != 'done' or s.state != 'cancel')
        # before compute
        old_rubric_ids = []
        old_class_ids = []

        old_class_ids = self.class_ids.mapped('class_conf_id').ids
        old_rubric_ids = self.class_ids.mapped('rubric_ids.paylip_rubric_conf_id').ids

        slip_ids.update_inputs()

        new_rubric_ids = []
        new_class_ids = []

        # after compute
        for slip in slip_ids:
            for line in slip.input_line_ids:
                if line.rule_id.rubric_id:
                    new_rubric_ids.append(line.rule_id.rubric_id.id)
                    new_class_ids.append(line.rule_id.rubric_id.classe_id.id)

        diff_class = list(set(new_class_ids).difference(set(old_class_ids)))
        for dc in diff_class:
            vals = {
                'payslip_run': self.id,
                'class_conf_id': dc,
            }
            self.env['hr.payslip.class'].create(vals)

        rubric_list = self.env['hr.payslip.rubric']
        diff_rubric = list(set(new_rubric_ids).difference(set(old_rubric_ids)))
        for dr in diff_rubric:
            rubric_conf_obj = self.env['hr.payslip.rubric.config'].browse(dr)
            class_id = self.env['hr.payslip.class'].search(
                [('payslip_run', '=', self.id), ('class_conf_id', '=', rubric_conf_obj.classe_id.id)], limit=1)
            vals = {
                'payslip_run': self.id,
                'paylip_rubric_conf_id': dr,
                'class_id': class_id.id,
            }

            rubric_list += self.env['hr.payslip.rubric'].create(vals)

        rub_ids = self.class_ids.mapped('rubric_ids')

        for rubric in rub_ids:
            if rubric.paylip_rubric_conf_id:
                self.env['hr.payslip.input'].search(
                    [('payslip_id.state', '!=', 'cancel'), ('payslip_id.payslip_run_id', '=', self.id),
                     ('rule_id.rubric_id', '=', rubric.paylip_rubric_conf_id.id), ('rubric_id', '=', False)]).write(
                    {'rubric_id': rubric.id})
                canceled_payslip = self.env['hr.payslip.input'].search(
                    [('payslip_id.state', '=', 'cancel'), ('payslip_id.payslip_run_id', '=', self.id),
                     ('rule_id.rubric_id', '=', rubric.paylip_rubric_conf_id.id)])
                canceled_payslip.write({'rubric_id': False})

    @api.one
    def compute_all(self):
        slip_done = []
        for slip in self.slip_ids:
            slip.compute_sheet()
            slip_done.append(slip.id)
            _logger.info("===== Payslip %s / %s done successfully ====" % (len(slip_done), len(self.slip_ids)))
        for rub_obj in self.env['hr.payslip.rubric'].search([('payslip_run', '=', self.id)]).filtered(
                lambda x: x.paylip_rubric_conf_id):
            line = self.env['hr.payslip.line'].search([('slip_id.payslip_run_id', '=', self.id), (
                'salary_rule_id.rubric_id', '=', rub_obj.paylip_rubric_conf_id.id)])
            line.write({'rubric_id': rub_obj.id})
        self.computed_payslips = True

    @api.model
    def create(self, vals):
        val_date_start = vals.get('date_start')
        val_date_end = vals.get('date_end')
        val_company_id = vals.get('company_id')
        domain0 = ['&', ('company_id', '=', val_company_id)]
        domain1 = ['&', ('date_start', '>=', val_date_start), ('date_start', '<=', val_date_end)]
        domain2 = ['&', ('date_end', '>=', val_date_start), ('date_end', '<=', val_date_end)]
        domain3 = ['&', ('date_start', '<=', val_date_start), ('date_end', '>=', val_date_end)]
        duplicated_run = self.search(domain0 + ['|', '|'] + domain1 + domain2 + domain3)
        if duplicated_run:
            raise UserError("Chevauchement de période de paie")
        res = super(hr_payslip_run, self).create(vals)
        res.generate_all()
        mail_mail_obj = self.env['mail.mail']
        template = self.env.ref('hr_copefrito_paie.email_template_notification_payslip_run')
        values = template.with_context().generate_email(res.id)
        #        values['email_to'] = self.env.user.email
        values['email_from'] = self.env.user.company_id.email
        operator_input_ids = self.env['operator.card'].search([('company_id', '=', res.company_id.id)])
        recipient_ids = [(4, recp_id.user_id.partner_id.id) for recp_id in operator_input_ids]
        pay_manager_group = self.env.ref('hr_copefrito_paie.group_pay_manager')
        for pay_manager in pay_manager_group.users:
            if self.company_id.id in pay_manager.company_ids.ids:
                recipient_ids.append((4, pay_manager.partner_id.id))
        values['recipient_ids'] = recipient_ids
        msg_id = mail_mail_obj.create(values)
        msg_id.send()
        mail_thread = self.env['mail.thread']
        mail_thread.message_post(type="notification", subtype="mt_comment", body=values['body'],
                                 partner_ids=recipient_ids)
        payslip_rubric_obj = self.env['hr.payslip.rubric.config'].search([('active', '=', False)])

        for class_id in res.class_ids:
            for rubric_id in class_id.rubric_ids.filtered(lambda x: x.code in payslip_rubric_obj.mapped('code')):
                rubric_id.active = False
        return res

    @api.one
    def make_waiting(self):
        self.state = 'waiting'
        self.is_waiting = True
        for payslip_id in self.slip_ids:
            if payslip_id not in ['waiting', 'done', 'cancel']:
                payslip_id.state = 'waiting'

    @api.one
    def make_close(self):
        self.state = 'close'
        for class_id in self.class_ids:
            for rubric_id in class_id.rubric_ids:
                rubric_id.state = 'closed'
        for payslip_id in self.slip_ids:
            if payslip_id.state not in ['done', 'cancel']:
                payslip_id.state = 'done'
        self.is_waiting = False

    @api.one
    def compute_sheet_generate(self):
        slip_pool = self.env['hr.payslip']

        from_date = self.date_start
        to_date = self.date_end
        credit_note = self.credit_note

        # all_employee = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)]).ids
        # employee_in_payslip = [slip.employee_id.id for slip in self.slip_ids]
        # emp_not_in_list = set(all_employee) - set(employee_in_payslip)

        emp_ids = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)], order="id asc").filtered(
            lambda e: e.has_active_contract()[0])
        emp_not_in_list = emp_ids - self.slip_ids.mapped('employee_id')

        if not emp_not_in_list:
            raise UserError(_("Les bulletins de tous les employées de la société sont déjà créés."))

        slip_ids = self.env['hr.payslip']
        for emp in emp_not_in_list:
            slip_data = slip_pool.onchange_employee_id(from_date, to_date, emp.id)
            res = {
                'employee_id': emp.id,
                'name': slip_data['value'].get('name', False),
                'struct_id': slip_data['value'].get('struct_id', False),
                'contract_id': slip_data['value'].get('contract_id', False),
                'payslip_run_id': self.id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids', False)],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids', False)],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': credit_note,
            }
            slip_ids += slip_pool.create(res)

        slip_ids.compute_sheet()

        for rub_obj in self.env['hr.payslip.rubric'].search([('payslip_run', '=', self.id)]):
            if rub_obj.paylip_rubric_conf_id:
                self.env['hr.payslip.input'].search([('payslip_id.payslip_run_id', '=', self.id), (
                    'rule_id.rubric_id', '=', rub_obj.paylip_rubric_conf_id.id)]).write({'rubric_id': rub_obj.id})

    @api.one
    def set_draft(self):
        for class_id in self.class_ids:
            for rubric_id in class_id.rubric_ids:
                rubric_id.state = 'draft' if rubric_id.input_ids else 'neutre'

    def compute_button_draft_visibility(self):
        self.button_draft_visibility = self.env.user.id == self.env.ref('base.user_root').id and self.state == 'close'

    @api.multi
    def set_inactive(self):
        for run in self:
            for p_class in run.class_ids:
                p_class.rubric_ids.write({'active': False})
                p_class.write({'active': False})
            run.slip_ids.write({'active': False})
            run.write({'active': False})

    # @api.multi
    # def set_active(self):
    #     for run in self:
    #         for p_class in run.class_ids:
    #             p_class.rubric_ids.write({'active': True})
    #             p_class.write({'active': True})
    #         for slip in run.slip_ids:
    #             print slip
    #             slip.write({'active': True})
    #         print "test",run.slip_ids
    #         run.write({'active': True})

    @api.multi
    def validate_all(self):
        for run in self:
            for c in run.class_ids.filtered(lambda c: c.state != 'neutre'):
                for rub in c.rubric_ids.filtered(lambda r: r.state != 'neutre'):
                    rub.make_verified()
                    rub.submit_input_ids()
                    rub.make_validate()

    @api.one
    def compute_is_verified(self):
        is_verified = True
        for c in self.class_ids:
            for rub in c.rubric_ids:
                for input_id in rub.input_ids:
                    if input_id.color_button != "green":
                        is_verified = False
                        break
        self.is_verified = is_verified

    @api.depends('responsable_employee_id')
    def compute_responsable_employee_id(self):
        if self.responsable_employee_id:
            self.responsable = self.responsable_employee_id.user_id

    @api.one
    def get_info_recap(self):

        def add_dic(dic1, dic2):
            result = {}
            for key in dic1.keys():
                if key != 'name':
                    result[key] = dic1[key] + dic2[key]
            result['name'] = dic1['name']
            return result

        result = {}
        payment_mode = {}
        transfer = {}
        mobile = {}
        cash = {}
        validated_slip_ids = self.slip_ids.filtered(lambda p: p.state == 'validate')
        for slip in validated_slip_ids:
            service_id = slip.contract_id.department_id
            line_ids = slip.line_ids
            retained_and_allocated = line_ids.filtered(
                lambda l: l.category_id == self.env.ref('hr_copefrito_paie.DED_DVRS'))
            ret_amount = retained_and_allocated.filtered(lambda l: l.rubric_id.paylip_rubric_conf_id.mouvement == '-')
            alc_amount = retained_and_allocated.filtered(lambda l: l.rubric_id.paylip_rubric_conf_id.mouvement == '+')
            net_to_pay = line_ids.filtered(
                lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_rule_basic_NETAPAYER')).amount
            service_recap = {
                'name': service_id.name,
                'number': 1,
                'gross': line_ids.filtered(
                    lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_salary_rule_BRUT')).amount,
                'cnaps': line_ids.filtered(
                    lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_payroll_rules_CNAPS_EMP')).amount,
                'ostie': line_ids.filtered(lambda l: l.salary_rule_id == self.env.ref(
                    'hr_copefrito_paie.hr_payroll_rules_RET_ORGM_EMP')).amount,
                'irsa': line_ids.filtered(
                    lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_payroll_rules_IRSA_DED')).amount,
                'retained': sum([a.amount for a in ret_amount]),
                'allocation': sum([a.amount for a in alc_amount]),
                'old_appoint': line_ids.filtered(
                    lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_rule_report')).amount,
                'new_appoint': line_ids.filtered(
                    lambda l: l.salary_rule_id == self.env.ref('hr_copefrito_paie.hr_rule_to_report')).amount,
                'net_to_pay': net_to_pay,
            }
            if result.has_key(service_id.id):
                result[service_id.id] = add_dic(result[service_id.id], service_recap)
            else:
                result[service_id.id] = service_recap

            def set_dict(dict, name, net_to_pay, id):
                val = {
                    'name': name,
                    'net_to_pay': net_to_pay,
                    'number': 1
                }
                if dict.has_key(id):
                    dict[id] = add_dic(dict[id], val)
                else:
                    dict[id] = val

            if slip.payment_mode == self.env.ref('hr_copefrito_paie.virement'):
                if slip.bank_account_id:
                    employee_bank = slip.bank_account_id.bank_id
                else:
                    employee_bank = slip.employee_id.bank_account_id.bank_id
                set_dict(transfer, employee_bank.name, net_to_pay, employee_bank.id)
            elif slip.payment_mode == self.env.ref('hr_copefrito_paie.mobile'):
                if slip.payment_mobile:
                    employee_mobile = slip.payment_mobile
                else:
                    employee_mobile = slip.employee_id.payment_mobile
                set_dict(mobile, employee_mobile.name, net_to_pay, employee_mobile.id)
            else:
                set_dict(cash, 'cash', net_to_pay, 0)
            payment_mode = {
                'transfer': transfer,
                'mobile': mobile,
                'cash': cash
            }

        return result, payment_mode

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(hr_payslip_run, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self._context.get('validate_run'):
            if view_type == 'tree':
                for node in doc.xpath('//tree'):
                    node.set('create', 'false')
                    node.set('delete', 'false')
            elif view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
            result['arch'] = etree.tostring(doc)
        return result


class hr_payslip_employees(osv.osv_memory):
    _inherit = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    @api.model
    def get_employees(self):
        context = dict(self._context or {})
        active_model = context.get('active_model')
        active_ids = context.get('active_ids')
        emp_ids = self.env['hr.employee'].search(
            [('company_id', '=', self.env[active_model].search([('id', 'in', active_ids)]).company_id.id)],
            order="id asc").ids
        emp_contract = self.env['hr.employee'].search([('contract_ids', '=', False)]).ids
        slip_emp_ids = []
        emp_list = []

        # list of employees already added in the payslip_run
        for slip in active_ids:
            emp_list.append(slip)

        # list of employees who don't have a contract
        for ec in emp_contract:
            emp_list.append(ec)

        for emp in emp_ids:
            if emp not in emp_list:
                slip_emp_ids.append(emp)

        return slip_emp_ids

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
                                    default=get_employees)



