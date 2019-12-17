# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv
import random
from openerp.exceptions import UserError
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree


class hr_employee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'mail.thread']
    _description = u'Employee-Enfant'

    @api.multi
    def _compute_display_name(self):
        result = []
        for emp in self:
            context = dict(self._context or {})
            if context.has_key("test_rubric") and context['test_rubric']:
                result.append((emp.id, "%s" % (emp.identification_cdi_id or emp.identification_id or '')))
            else:
                result.append((emp.id, "%s " % (emp.name)))
        names = dict(result)
        for record in self:
            record.display_name = names.get(record.id, False)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('identification_cdi_id', operator, name)]
        picks = self.search(domain + args, limit=limit)
        result = []
        for emp in picks:
            context = dict(self._context or {})
            if context.has_key("test_rubric") and context['test_rubric']:
                result.append((emp.id, "%s " % (emp.identification_cdi_id or emp.identification_id)))
            else:
                result.append((emp.id, "%s  " % (emp.name)))
        return result

    @api.model
    def _get_default_employee_tag(self):  ##-
        return self.env['hr.employee.category'].search([('name', 'in', ['employe'])]).ids

    @api.multi
    @api.depends('enfant_ids')
    def _calculate_number_of_enfants(self):
        """Comppute number of child
           under 18 for employee
        """
        for rec in self:
            if rec.enfant_ids:
                rec.nb_enfants = len(rec.enfant_ids)
                res = 0
                for child in rec.enfant_ids:
                    if child.age < 18:
                        res += 1
                child_allocated = rec.enfant_ids.filtered(lambda c: c.age >= 18)
                if child_allocated:
                    rec.children_allocated = len(child_allocated)
                rec.children = res

    def create(self, cr, uid, vals, context=None):
        print "create employe + user"
        employee_obj = self.pool.get('hr.employee')
        user_obj = self.pool.get('res.users')

        # test matricule employé
        if vals['identification_cdi_id'] == 0 or not vals['identification_cdi_id']:
            print "Matricule nulle acceptée (create)"
        else:
            id_cdi = employee_obj.search(cr, uid, [('identification_cdi_id', '=', vals['identification_cdi_id'])])
            if id_cdi:
                raise osv.except_osv(u'OUPS!',
                                     u'Le N° Matricule Employé %s existe déjà!' % vals['identification_cdi_id'])
        # if not vals['user_id']:
        #     employee_name = vals['name']
        #     # print "-------> name : ",employee.name_related
        #     random_name = "".join(employee_name.lower().split()) + str(random.randrange(1, 999999))  ##-
        #     data_user = {
        #         'login': random_name,
        #         'name': random_name,
        #         'email': random_name + "@",
        #     }
        #     assignee_id = int(user_obj.create(cr, uid, data_user))  # create user
        #     vals['user_id'] = assignee_id
        #     print "Update Employee status : ", assignee_id
        return super(hr_employee, self).create(cr, uid, vals, context=context)

    @api.multi  ##-
    def write(self, vals):
        if vals.has_key('identification_cdi_id') and vals.get('identification_cdi_id'):
            for rec in self:
                active_contract = rec.contract_ids.filtered(lambda c: c.state in ['open', 'renewed', 'active'])
                if len(active_contract) > 1:
                    raise UserError(_("Un employé ne peut pas avoir plusieurs contract actifs"))
                dupl_perm = self.search(
                    [('identification_cdi_id', '=', vals['identification_cdi_id'].rjust(6, "0"))]) - rec
                dupl = self.search([('identification_cdi_id', '=', vals['identification_cdi_id'])]) - rec
                if (not active_contract and dupl) or (dupl and active_contract.status != 'permanent'):
                    raise UserError(_(u'Le N° Matricule Employé %s existe déjà!' % vals['identification_cdi_id']))
                elif (active_contract.status == 'permanent' and dupl_perm):
                    raise UserError(
                        _(u'Le N° Matricule Employé %s existe déjà!' % vals['identification_cdi_id'].rjust(6, "0")))
                elif active_contract.status == 'permanent':
                    vals.update({'identification_cdi_id': vals.get('identification_cdi_id').rjust(4, "0")})
        # self.env['history.model'].track_edit(active_ids=self.ids, active_model='hr.employee', vals=vals)

        res = super(hr_employee, self).write(vals)
        return res

    @api.one
    def deleted_left_0_from_matricule(self):
        matricule = self.identification_cdi_id
        if matricule:
            while matricule[0] == '0':
                matricule = matricule[1:]
            if len(matricule) < 3 and matricule.isdigit():
                matricule = matricule.rjust(3, "0")
            self.register = matricule

    #    @api.one
    #    @api.onchange('code_poste')
    #    def _onchange_code_poste(self):
    #        if self.code_poste:
    #            self.job_id = self.code_poste.job_id
    #            self.department_id = self.code_poste.job_id.service_id
    #
    #    @api.one
    #    @api.onchange('job_id')
    #    def _onchange_poste(self):
    #        if self.job_id:
    #            self.code_poste = self.job_id.code
    #            self.department_id = self.job_id.service_id
    #
    #    @api.one
    #    @api.onchange('code_service')
    #    def _onchange_code_service(self):
    #        self.department_id = self.code_service.service_id
    #        if not (self.department_id.id == self.job_id.service_id.id):
    #            self.code_poste = False
    #            self.job_id = False
    #
    #    @api.multi
    #    def onchange_department_id(self, department_id):
    #        result = super(hr_employee,self).onchange_department_id(department_id)
    #        department_data = self.env['hr.department'].browse([department_id])
    #        value = dict(result['value'] or {})
    #        value['code_service'] = department_data.code.id
    #        result['value'] = value
    #        return result

    #    @api.one
    #    @api.depends('contract_ids')
    #    def _compute_service_poste(self):
    #        contract_state_open = self.contract_ids.filtered(lambda c: c.state == 'open')
    #        if contract_state_open:
    #            self.department_id = contract_state_open.department_id
    #            self.job_id = contract_state_open.job_id
    #            self.code_poste = self.job_id.code
    #            self.code_service = self.department_id.code
    #        print "Service", self.department_id
    #        print "Post", self.job_id

    num_cnaps = fields.Char(u'N° CNAPS')
    # identification_cdi_id = fields.Integer(u'N° Matricule Employé')
    identification_cdi_id = fields.Char(u'N° Matricule Employé')
    enfant_ids = fields.One2many('hr.enfant', 'property_id',
                                 string=u'Information Enfant')
    nb_enfants = fields.Integer(compute=_calculate_number_of_enfants,
                                string=u'Nombre total d\'enfant', store=True)
    children = fields.Integer(compute=_calculate_number_of_enfants,
                              string=u'Nombre d\'enfant moins de 18ans',
                              help=u'Nbr Enfant(s) moins de 18ans',
                              readonly=True, store=True)
    children_allocated = fields.Integer(compute=_calculate_number_of_enfants,
                                        string=u'Nombre d\'enfant plus de 18ans',
                                        help=u'Nbr Enfant(s) plus de 18ans ayant droit allocation',
                                        readonly=True)
    category_ids = fields.Many2many('hr.employee.category', 'employee_category_rel', 'emp_id', 'category_id', 'Tags',
                                    default=_get_default_employee_tag)  ##-
    tel_for_payment = fields.Char(u'N° Tel. paiement', readonly=False)  ##-
    agency_id = fields.Many2one('agency.default.data',
                                string=u'Agence')  ##- ,required=True removed 13/01/17 SFD TO update
    # company_id = fields.Many2one('res.company', u'Société', required=True)  ##-
    company_id = fields.Many2one('res.company', string=u'Société', default=lambda self: self.env.user.company_id,
                                 required=True)
    num_cin = fields.Char(u'N° CIN')
    date_cin = fields.Date(u'Date de délivrance CIN')
    lieu_cin = fields.Char(u'Lieu de délivrance CIN')
    job_id = fields.Many2one('hr.job', u'Fonction', readonly=True)
    department_id = fields.Many2one('hr.department', string=u"Service", readonly=True)
    code_poste = fields.Many2one('hr.code.poste', u'Code poste', required=False, readonly=True)
    code_service = fields.Many2one('hr.code.service', u'Code service', required=False, readonly=True)
    marital = fields.Selection(
        [('single', 'Célibataire'), ('married', 'Marié(e)'), ('widower', 'Veuf(ve)'), ('divorced', 'Divorcé(e)')],
        string=u"Situation matrimoniale")
    surname = fields.Char(u'Surnom')
    name_conjunct = fields.Char(string=u"Conjoint")
    job_conjunct = fields.Char(string=u"Emploi")
    birthday_conjunct = fields.Date(string=u"Date de naissance du conjoint")
    age_conjunct = fields.Integer(string=u"Age", readonly=True, compute='_calculate_age_conjunct')
    tel_home = fields.Char(string=u"Tél domicile")
    emergency_person = fields.Char(string=u"Personne à contacter en cas d'urgence")
    tel_emergency = fields.Char(string=u"Tél en cas d'urgence")
    personnal_email = fields.Char(string=u"Email")
    address_bis_id = fields.Char(string=u"Adresse professionnelle")
    tel_flotte = fields.Char(string=u"N° Tél flotte")
    # payment_mode = fields.Selection(string=u"Mode de paiement", selection=[('cash', 'Cash'), ('transfer', 'Virement'), ('mobile', 'Mobile banking') ])
    payment_mode = fields.Many2one("hr.payslip.payment.mode", string=u"Mode de paiement", required=True)
    payment_mobile = fields.Many2one('hr.payslip.payment.mobile', string=u"Mobile banking")
    payment_type = fields.Selection(related="payment_mode.payment_type", string=u"Type de mode de paiement")
    num_contract = fields.Char(u'Num contrat', compute="_get_data_contract")
    date_start = fields.Date(u"Date d'embauche", compute="_get_data_contract")
    date_end = fields.Date(u"Date de débauche", compute="_get_data_contract")
    csp_id = fields.Many2one("hr.contract.qualification", u"CSP")
    address_home = fields.Char('Adresse personnelle')
    contract_ids = fields.One2many('hr.contract', 'employee_id', string="contrats")
    register = fields.Char(string="Matricule normalisé", compute="deleted_left_0_from_matricule")

    # not_draft = fields.Boolean(compute='compute_not_draft', default = False, store=True)
    # payment_category = fields.Selection(
    #     [('mobile', 'Mobile'), ('bank', 'Virement'), ('check', 'Chèque'), ('cash', 'Espèces')],
    #     string=u"Mode de paiement", required=True, default='bank', track_visibility='onchange')

    # @api.multi
    # def compute_not_draft(self):
    #     contracts = self.env['hr.contract'].filtered(lambda x: x.employee_id == self.id)
    #     for contract in contracts:
    #         if contract.state != 'draft':
    #             not_draft = True
    #     return not_draft

    @api.one
    def _get_data_contract(self):
        if self.sudo().contract_ids:
            opened_contract = self.sudo().contract_ids.filtered(lambda c: c.state in ['open', 'renewed', 'active'])
            if opened_contract:
                self.num_contract = opened_contract.num_contract
                self.date_start = opened_contract.date_start
                self.date_end = opened_contract.date_end

    @api.onchange('code_service', 'department_id')
    def dynamic_domain(self):
        if self.code_service or self.department_id:
            return {'domain': {'job_id': [('service_id.id', '=', "%s" % self.department_id.id)],
                               'code_poste': [('job_id.service_id.id', '=', "%s" % self.department_id.id)]}}

    @api.multi
    @api.depends('birthday_conjunct')
    def _calculate_age_conjunct(self):
        for rec in self:
            if rec.birthday_conjunct:
                now = datetime.today().date()
                birthday = datetime.strptime(rec.birthday_conjunct, '%Y-%m-%d').date()
                age = relativedelta(now, birthday)
                rec.age_conjunct = age.years

    # remove sum of identification_cdi_id when groupby in employee
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'identification_cdi_id' in fields:
            fields.remove('identification_cdi_id')
        return super(hr_employee, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby,
                                                   lazy=lazy)

    @api.one
    def has_active_contract(self):
        if self.contract_ids.filtered(lambda c: c.state in ['open', 'renewed', 'active']):
            return True
        return False

    # @api.multi
    # def unlink(self):
    #     hr_holidays_ids = self.env['hr.holidays'].search([('employee_id', 'in', self.ids)])
    #     for hr_holiday_id in hr_holidays_ids:
    #         hr_holiday_id.state = 'draft'
    #     hr_holidays_ids.unlink()
    #     return super(hr_employee, self).unlink()

    @api.one
    def has_closed_contract(self):
        if self.contract_ids.filtered(lambda c: c.state in ['close']):
            return True
        return False

    @api.model
    def unlink_duplicate_employee(self):
        all_emp = self.search([])
        for rec in all_emp:
            dupl_emp = self.search([('name', '=', rec.name)]) - rec
            if dupl_emp and not rec.contract_ids:
                linked_hol = self.env['hr.holidays'].search([('employee_id', '=', rec.id)])
                linked_hol.write({'state': 'draft'})
                linked_hol.unlink()
                rec.unlink()

    @api.one
    def get_matched_contract(self, slip_end):

        def is_in_the_same_month(d1, d2):
            date1 = datetime.strptime(d1, "%Y-%m-%d")
            date2 = datetime.strptime(d2, "%Y-%m-%d")
            return date1.month == date2.month and date1.year == date2.year

        return self.contract_ids.filtered(lambda c: is_in_the_same_month(c.date_start, slip_end)).ids

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(hr_employee, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        active_user = self.env.user
        if active_user.has_group('hr_copefrito_paie.group_direction'):
            if view_type == 'tree':
                for node in doc.xpath('//tree'):
                    node.set('create', 'false')
                    node.set('delete', 'false')
            elif view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        if not active_user.has_group('hr_copefrito_paie.group_pay_operateur'):
            if view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        result['arch'] = etree.tostring(doc)
        return result
