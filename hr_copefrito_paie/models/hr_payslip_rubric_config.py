# -*- coding: utf-8 -*-

import unicodedata, re

from openerp import models, api, fields
from openerp.exceptions import ValidationError
from openerp.exceptions import UserError
from lxml import etree

# STATUT = [
#     ('permanent', 'Permanent'),
#     ('journalier', 'Journalier'),
#     ('stagiaire', 'Stagiaire'),
#     ('visiteur', 'Visiteur')
# ]
STATUT = [
    ('permanent', 'Permanent'),
    ('journalier', 'Journalier'),
    ('mixte', 'Mixte')
]

MOUVEMENT = [
    ('+', 'Positif'),
    ('-', u'Négatif')
]

TYPE = [
    ('fixe', 'Fixe'),
    ('normal', 'Variable'),
    ('total', 'Total'),
    ('regle', u'Règle'),
]


class HrPayslipRubricConfig(models.Model):
    _name = 'hr.payslip.rubric.config'
    _order = 'sequence'
    _sql_constraints = [
        ('hr_payslip_rubric_config_code_uniq',
         'UNIQUE (code)',
         'Code déjà existant')]

    classe_id = fields.Many2one("hr.payslip.class.config", "Classe", required=True)
    name = fields.Char("Nom", required=True)
    code = fields.Char("Code", required=True)
    code_class = fields.Char("code_class", related="classe_id.code", readonly=True)
    code_temp = fields.Char("code_temp", required=False)
    rule_id = fields.Many2one('hr.salary.rule', u'Règle', ondelete='cascade')
    rule_info_id = fields.Many2one('hr.salary.rule', u'Règle info', ondelete='cascade')
    rubric_link = fields.Many2one('hr.payslip.rubric.config', u'Rubrique reliée')
    rubric_link_ids = fields.Many2many('hr.payslip.rubric.config', "hr_payslip_rubric_link", "rub_id_1", "rub_id_2",
                                       u'Rubriques reliées')
    hr_department_ids = fields.Many2many("hr.department", "hr_rubric_conf_department_id", "rubric_conf_id",
                                         "service_id", string=u"Service")
    status = fields.Selection(STATUT, string=u'Statut', default='permanent')
    mouvement = fields.Selection(MOUVEMENT, string=u"Mouvement", default="+")
    product_uom = fields.Many2one('product.uom', u'Unité de Valeur',
                                  default=False)
    type = fields.Selection(TYPE, string=u"Type", default='normal')
    company_ids = fields.Many2many('res.company', string=u"Société")
    responsable_ids = fields.Many2many('res.users', string=u"Opérateurs de Saisie", readonly=False)
    is_readonly = fields.Boolean('Readonly')
    sequence = fields.Integer('Sequence')
    summed_rubric = fields.Many2many('hr.payslip.rubric.config', "hr_payslip_rubric_sum", "rub_id_1", "rub_id_2",
                                     u'Rubriques à sommer')
    is_total_readonly = fields.Boolean(default=False)
    contract_ids = fields.Many2many('hr.contract', "hr_payslip_rubric_hr_contract_rel", "rub_id", "contract_id",
                                    string=u"Contrats liés")
    invisible_qty = fields.Boolean(u"Ne pas afficher quantité")
    summed_class = fields.Many2many('hr.payslip.class.config', string=u"Classes à sommer")
    active = fields.Boolean(default=True, string="Active")
    non_taxable = fields.Boolean(u"Non taxable")

    @api.model
    def fields_get(self, fields=None):
        fields_to_hide = ['code_class',
                          'code_temp',
                          'is_total_readonly'
                          ]
        # you can set this dynamically
        res = super(HrPayslipRubricConfig, self).fields_get(fields)
        for field in fields_to_hide:
            res[field]['selectable'] = False
        return res

    @api.multi
    @api.depends('code', 'name')
    def name_get(self):
        result = []
        for rubric in self:
            if rubric.name:
                result.append((rubric.id, str(rubric.code) + " - " + rubric.name))
            else:
                result.append((rubric.id, rubric.code))
        return result

    @api.multi
    def button_toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. 
        :rtype: object
        """
        for record in self:
            record.active = not record.active
            payslip_run_ids = self.env['hr.payslip.run'].search([('state', '!=', 'validate')])
            payslip_ids = self.env['hr.payslip'].search([('payslip_run_id', 'in', payslip_run_ids.ids)])
            payslip_rubric_ids = self.env['hr.payslip.rubric'].search([('payslip_run', 'in', payslip_run_ids.ids)])
            contract_ids = self.env['hr.contract'].search([])
            contract_rubric_ids = self.env['hr.contract.rubric']
            if record.active == False:
                for run in payslip_run_ids:
                    for class_id in run.class_ids:
                        for rubric_id in class_id.rubric_ids.filtered(lambda x: x.code == record.code):
                            rubric_id.active = False
                        for line in class_id.slip_line_ids.filtered(lambda x: x.code_rubric == record.code):
                            line.active = False
                for payslip in payslip_ids:
                    for payslip_input in payslip.input_line_ids.filtered(lambda x: x.code_rubric == record.code):
                        payslip_input.active = False
                    for line in payslip.line_ids.filtered(lambda x: x.sequence == record.code):
                        line.active = False
                for rubric in payslip_rubric_ids.filtered(lambda x: x.code == record.code):
                    rubric.active = False
                for contract in contract_ids:
                    for rubric in contract.rubric_ids.filtered(lambda x: x.code == record.code):
                        rubric.active = False
            elif record.active == True:
                rule_ids = self.env['hr.salary.rule'].search([('active', '=', False), ('rubric_id', '=', record.id)])
                payslip_line_ids = self.env['hr.payslip.line'].search(
                    [('active', '=', False), ('salary_rule_id', '=', record.rule_id.id)])
                payslip_input_ids = self.env['hr.payslip.input'].search(
                    [('active', '=', False), ('rule_id', '=', record.rule_id.id)])
                for contract_id in contract_ids:
                    contract_rubric_ids += self.env['hr.contract.rubric'].search(
                        [('active', '=', False), ('rubric_conf', '=', record.id), ('contract_id', '=', contract_id.id)],
                        order='create_date desc', limit=1)
                payslip_rubric_ids = self.env['hr.payslip.rubric'].search(
                    [('active', '=', False), ('paylip_rubric_conf_id', '=', record.id)])
                rule_ids.write({'active': True})
                payslip_line_ids.write({'active': True})
                payslip_input_ids.write({'active': True})
                if len(contract_rubric_ids) > 0:
                    contract_rubric_ids.write({'active': True})
                payslip_rubric_ids.write({'active': True})

    @api.one
    @api.constrains('type')
    def _check_type(self):
        if self.type == 'total':
            class_total_ids = (self.env.ref('hr_copefrito_paie.CLASS_SUM_RUB') | self.env.ref(
                'hr_copefrito_paie.CLASS_SUM_CLASS')).ids
            rubric_total = self.env['hr.payslip.rubric.config'].search(
                [('type', '=', 'total'), ('classe_id', '=', self.classe_id.id), ('id', '!=', self.id),
                 ('classe_id', 'not in', class_total_ids)])
            if rubric_total: raise ValidationError('Une rubrique de type total pour cette classe existe déjà.')

    @api.one
    @api.onchange('code_temp')
    def _onchange_code_temp(self):
        # self.code = self.code_class * 100 + self.code_temp
        if self.code_temp and self.code_class:
            self.code = self.code_class + self.code_temp

    @api.constrains('code_temp')
    def _constrains_code_rubric(self):
        if len(str(self.code_temp)) > 2:
            raise ValidationError('Le code de la rubrique ne doit pas depasser les 3 chiffres')

    @api.model
    def create(self, vals):
        if not vals.get('code') and vals.get('code_temp'):
            vals['code'] = self.env['hr.payslip.class.config'].browse(vals['classe_id']).code + vals['code_temp'].rjust(
                2, "0")
        if vals['classe_id'] in (self.env.ref('hr_copefrito_paie.CLASS_SUM_RUB') | self.env.ref(
                'hr_copefrito_paie.CLASS_SUM_CLASS')).ids:
            vals['type'] = 'total'
            vals['code'] = self.env['hr.payslip.class.config'].browse(vals['classe_id']).code + vals['code_temp']
        elif vals['type'] == 'total':
            vals['summed_rubric'] = [(6, 0, self.search([('classe_id', '=', vals['classe_id'])]).ids)]
            vals['code_temp'] = "99"
            vals['code'] = self.env['hr.payslip.class.config'].browse(vals['classe_id']).code + "99"
        vals['sequence'] = self.get_sequence(vals.get('code', "9999"))

        def is_int(code):
            try:
                return int(code)
            except ValueError:
                return False

        if not is_int(vals['code_temp']) and is_int(vals['code_temp']) != 0:
            raise UserError('Le code rubrique doit être un entier')

        res = super(HrPayslipRubricConfig, self).create(vals)

        if not vals.has_key('company_id'): vals['company_id'] = False

        if not vals.has_key('rule_id'):
            vals['rule_id'] = False
        if not vals["rule_id"]:
            if vals["type"] != 'total': self.sudo()._create_rule(vals, res)
            if vals["type"] == 'total': self.sudo().create_rule_total(vals, res)
        else:
            rule = self.env['hr.salary.rule'].browse(vals['rule_id'])
            rule.rubric_id = res.id

        contrat_ids = None
        if vals['type'] == 'fixe':
            val_rub = {
                'rubric_ids': [(0, 0, {'rubric_conf': res.id, 'montant': 0})]
            }
            domain_contrat = []
            if vals.get('hr_department_ids') and vals['hr_department_ids'][0] and len(vals['hr_department_ids'][0]) > 2:
                domain_contrat.append(('department_id', 'in', vals['hr_department_ids'][0][2]))
            if vals.get('company_id'):
                domain_contrat.append(('employee_id.company_id', '=', vals['company_id']))

            contrat_ids = self.env['hr.contract'].search(domain_contrat)
            for contrat in contrat_ids:
                contrat.write(val_rub)

        # res.contract_ids.write({'variable_rubric_ids': [(4, res.id)]})

        # for rub in self:
        #     if rub.rubric_link and not self._context.get('from_parent'):
        #         rub.rubric_link.with_context(from_parent=True).write({'rubric_link': rub.id})

        return res

    @api.model
    def _create_rule(self, vals, res):
        class_env = self.env['hr.payslip.class.config']
        rule_env = self.env['hr.salary.rule']

        class_obj = class_env.search([('id', '=', vals['classe_id'])])
        code_rule_rub_info = unicodedata.normalize("NFKD", unicode(vals['name'] + 'INFO')).encode("ascii",
                                                                                                  "ignore").upper()
        code_rule_rub_info = re.sub(r"[^\w]+", "_", code_rule_rub_info)

        last_rule_info = rule_env.search([('category_id', '=', self.env.ref("hr_copefrito_paie.INFO_RUBR").id)],
                                         limit=1, order='sequence desc')
        seq_rule_info = last_rule_info.sequence + 1 if last_rule_info else 0
        code_rule = 'INFO_' + str(vals['code'])
        fixe_val = 'is_incomplete = contract.check_incomplete_month(payslip.date_from, payslip.date_to)[0][0]' if vals.get(
            'type') == 'fixe' else ''
        fixe_condition = 'or (rub.rubric_conf.status == \'permanent\' and is_incomplete)' if vals.get(
            'type') == 'fixe' else ''
        amount_python_compute_info = """

rub = contract.rubric_ids.filtered(lambda r: str(r.rubric_conf.code) == '%s')

res = (inputs.%s.amount if inputs.%s and inputs.%s.amount else 0)     

resultat = 0
%s
if rub and rub.rubric_conf.type == 'fixe' :
	if rub.rubric_conf.status == 'journalier' %s: resultat = res
	else : resultat = rub.montant
else : resultat = res
result = resultat

		""" % (vals['code'], code_rule, code_rule, code_rule, fixe_val, fixe_condition)

        data_rule_info = {
            'name': vals['name'] + ' INFO',
            'code': code_rule,
            'category_id': self.env.ref("hr_copefrito_paie.INFO_RUBR").id,
            'sequence': seq_rule_info,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': amount_python_compute_info,
            'appears_on_payslip': False,
            'rubric_id': res.id,
        }

        # if vals['company_id']:
        #     data_rule_info['condition_select'] = 'python'
        #     data_rule_info['condition_python'] = """ result =  employee.company_id.id == %s """ % (vals['company_id'])

        rule_info = rule_env.create(data_rule_info)

        # amount_python_compute_rule = "a"

        #         if not vals['rubric_link'] :
        #             amount_python_compute_rule = """
        # result =  %s(%s or 0)
        #         """  %(vals['mouvement'], code_rule)
        #
        #         else :
        #             rubric = self.browse(vals['rubric_link'])
        #
        #             amount_python_compute_rule_linked = """
        # result =  %s%s  if  %s and %s > %s else 0
        #         """  %(rubric.mouvement, rubric.rule_info_id.code, rubric.rule_info_id.code, rubric.rule_info_id.code, code_rule)
        #
        #             rubric.rule_id.amount_python_compute = amount_python_compute_rule_linked
        #
        #             amount_python_compute_rule = """
        # result =  %s%s  if  %s and %s > %s else 0
        #         """  %(vals['mouvement'], code_rule, code_rule, code_rule, rubric.rule_info_id.code)

        data_rule = {
            'name': vals['name'],
            'code': vals['name'],
            'category_id': class_obj.category_id.id,
            'sequence': int(vals['code']),
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': "",
            'appears_on_payslip': True,
            'rubric_id': res.id,
        }

        # if vals['company_id']:
        #     data_rule['condition_select'] = 'python'
        #     data_rule['condition_python'] = """ result =  employee.company_id.id == %s """ % (vals['company_id'])

        rule = rule_env.create(data_rule)

        self.sudo()._create_input(vals, rule_info.id)

        self.sudo()._add_to_structure(rule_info.id)
        self.sudo()._add_to_structure(rule.id)

        res.write({'rule_id': rule.id, 'rule_info_id': rule_info.id})

        if not vals.get('rubric_link_ids'):
            amount_python_compute_rule = "result =  %s(%s or 0)" % (res.mouvement or '+', code_rule)
            res.rule_id.amount_python_compute = amount_python_compute_rule

        else:
            added_ids = []
            for link_id in res.rubric_link_ids:
                added_ids += link_id.rubric_link_ids.ids
            added_ids = list(set(added_ids))
            (res + res.rubric_link_ids + self.browse(added_ids))._create_rubric_link_rule()

    @api.model
    def compute_amount_rule(self, vals, res):
        class_obj = res.classe_id

        if res.classe_id not in (
                self.env.ref('hr_copefrito_paie.CLASS_SUM_RUB') | self.env.ref('hr_copefrito_paie.CLASS_SUM_CLASS')):
            # amount_python_compute = """result = categories.%s """ % (class_obj.category_id.code)
            seq_total = int(class_obj.code) * 100 + 99
        # if res.classe_id == self.env.ref('hr_copefrito_paie.CLASS_DED_REG'):
        #     seq_total = 1099
        else:
            class_code, pre_code = ("SR", 1000) if res.classe_id == self.env.ref(
                'hr_copefrito_paie.CLASS_SUM_RUB') else ("SC", 1200)
            vals_code = res.check_code_total(vals['code'], class_code) if vals.has_key('code') else False
            if vals_code:
                seq_total = pre_code + vals_code
            else:
                raise ValidationError('Mauvais code rubrique de type total')
        # code_to_sum = "0"
        # if res.summed_rubric:
        #     list_sum = []
        #     for rub in res.summed_rubric:
        #         if rub.type == 'regle':
        #             list_sum.append(rub.rule_id.code)
        #         else:
        #             list_sum.append("%s%s" % (rub.mouvement, rub.rule_info_id.code))
        #     code_to_sum = "sum((%s))" % (','.join(list_sum),)
        # elif res.summed_class:
        #     code_to_sum = "sum((%s))" % (','.join(['categories.%s' % c for c in res.summed_class.mapped('category_id.code')]),)
        # amount_python_compute = """result = %s """ % code_to_sum

        if res.type == 'total' and res.summed_rubric or res.summed_class:
            code_to_sum = "0"
            if res.summed_rubric:
                list_sum = []
                for rub_sum in res.summed_rubric:
                    if rub_sum.type == 'regle' and rub_sum != self.env.ref('hr_copefrito_paie.RUBRIC_100'):
                        list_sum.append(rub_sum.rule_id.code)
                    else:
                        list_sum.append("%s%s" % (rub_sum.mouvement, rub_sum.rule_info_id.code))
                code_to_sum = "sum((%s))" % (','.join(list_sum),)
            elif res.summed_class:
                code_to_sum = "sum((%s))" % (
                    ','.join(['categories.%s' % c for c in res.summed_class.mapped('category_id.code')]),)
            amount_python_compute = """result = %s """ % code_to_sum
        #     res.rule_id.amount_python_compute = amount_python_compute

        data_rule = {
            'name': vals['name'],
            'code': vals['name'],
            'category_id': self.env.ref("hr_copefrito_paie.INFO").id,
            'sequence': seq_total,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': amount_python_compute,
            'appears_on_payslip': True,
            'rubric_id': res.id,
        }

        return data_rule

    @api.model
    def create_rule_total(self, vals, res):
        rule_env = self.env['hr.salary.rule']
        data_rule = self.compute_amount_rule(vals, res)
        rule = rule_env.create(data_rule)
        self.sudo()._add_to_structure(rule.id)
        new_val = {'rule_id': rule.id, 'is_total_readonly': True}
        res.write(new_val)

    @api.onchange('classe_id', 'type')
    def onchange_classe_id_type(self):
        if self.classe_id not in (self.env.ref('hr_copefrito_paie.CLASS_SUM_CLASS') | self.env.ref(
                'hr_copefrito_paie.CLASS_SUM_RUB')) and self.type == "total":
            self.summed_rubric = [(6, 0, self.search([('classe_id', '=', self.classe_id.id)]).ids)]
            self.code_temp = "99"
        if self.classe_id == self.env.ref('hr_copefrito_paie.CLASS_SUM_RUB'):
            self.type = 'total'
        if self.classe_id == self.env.ref('hr_copefrito_paie.CLASS_SUM_CLASS'):
            self.type = 'total'

    @api.model
    def check_code_total(self, code, prefix):
        int_code = code.lstrip(prefix)
        try:
            return int(int_code)
        except ValueError:
            return False

    @api.model
    def _create_input(self, vals, id_rule):
        """ Create new rule input """
        obj_input = self.env['hr.rule.input']
        code_rule = 'INFO_' + str(vals['code'])
        data_input = {
            'name': vals['name'],
            'code': code_rule,
            'input_id': id_rule,
        }
        obj_input.create(data_input)

    @api.model
    def _add_to_structure(self, id_rule):
        """ Add new rule to structure salary rule """
        struct_id = self.env.ref('hr_copefrito_paie.hr_payroll_structure_structure_cdi_r0')
        struct_id.write({'rule_ids': [(4, id_rule)]})

    @api.multi
    def write(self, vals):
        rubric_link_dic = {}
        rubric_link_contract = {}
        rub_status = {}
        classe_sr_sc = (
                self.env.ref('hr_copefrito_paie.CLASS_SUM_CLASS') | self.env.ref('hr_copefrito_paie.CLASS_SUM_RUB'))
        for rub in self:
            rubric_link_dic[rub.id] = rub.rubric_link_ids.ids
            rubric_link_contract[rub.id] = rub.contract_ids.ids
            rub_status[rub.id] = rub.status
            if vals.get('type') == 'total' and vals.get('classe_id') not in classe_sr_sc.ids:
                vals['summed_rubric'] = [(6, 0, (self.search([('classe_id', '=', vals['classe_id'])]) - rub).ids)]
        if vals.has_key('code'):
            vals['sequence'] = self.get_sequence(vals.get('code', "9999"))
        res = super(HrPayslipRubricConfig, self).write(vals)

        for rub in self:
            if vals.has_key('name'):
                rub.rule_id.name = self.name

            if vals.has_key('company_id'):
                if vals['company_id']:
                    if vals['company_id']:
                        rub.rule_id.condition_select = 'python'
                        rub.rule_id.condition_python = """ result =  employee.company_id.id == %s """ % (
                            vals['company_id'])
                        if rub.rule_info_id:
                            rub.rule_info_id.condition_select = 'code'
                            rub.rule_info_id.condition_python = """ result =  employee.company_id.id == %s """ % (
                                vals['company_id'])
                    else:
                        rub.rule_id.condition_select = 'none'
                        if rub.rule_info_id: rub.rule_info_id.condition_select = 'none'

            # if we link a rubric with another rubric wich linked rubrics this rubric should be linked with the linked rubrics
            added_ids = []
            added_rubric = list(set(rub.rubric_link_ids.ids) - set(rubric_link_dic[rub.id]))
            for new_rub in self.browse(added_rubric):
                added_ids += new_rub.rubric_link_ids.ids
            if vals.has_key("rubric_link_ids") and not self._context.get('from_link'):
                if rub.rubric_link_ids:
                    (rub + rub.rubric_link_ids + self.browse(list(set(added_ids))))._create_rubric_link_rule()
                else:
                    rub._delete_rubric_link_rule()

            deleted_rubric = list(set(rubric_link_dic[rub.id]) - set(rub.rubric_link_ids.ids))
            if deleted_rubric and not self._context.get('from_link'):
                self.browse(deleted_rubric)._delete_rubric_link_rule()

            for input in rub.rule_info_id.input_ids:
                input.write({'name': rub.name})

            if rub.type == 'total' and (vals.has_key('summed_rubric') or vals.has_key('summed_class')):
                code_to_sum = "0"
                if vals.has_key('summed_rubric'):
                    list_sum = []
                    for rub_sum in rub.summed_rubric:
                        if rub_sum.type == 'regle' and rub_sum != self.env.ref('hr_copefrito_paie.RUBRIC_100'):
                            list_sum.append(rub_sum.rule_id.code)
                        else:
                            list_sum.append("%s%s" % (rub_sum.mouvement, rub_sum.rule_info_id.code))
                    code_to_sum = "sum((%s))" % (','.join(list_sum),)
                # code_to_sum = "sum((%s))" % (','.join(rub.summed_rubric.mapped('rule_info_id.code')),)
                elif vals.has_key('summed_class'):
                    code_to_sum = "sum((%s))" % (
                        ','.join(['categories.%s' % c for c in rub.summed_class.mapped('category_id.code')]),)
                amount_python_compute = """result = %s """ % code_to_sum
                rub.rule_id.amount_python_compute = amount_python_compute

            if vals.has_key('status') and rub_status[rub.id] != rub.status:
                rub.onchange_status()
        return res

    @api.multi
    def unlink(self):
        for rubric_conf in self:
            rub_cont = self.env['hr.contract.rubric'].search([('rubric_conf', '=', rubric_conf.id)])
            rub_cont.unlink()
            id_rubric = rubric_conf.rule_id.id
            rubric_conf.rule_info_id.input_ids.unlink()
            rubric_conf.rule_info_id.unlink()
            if id_rubric:
                rub = self.env['hr.salary.rule'].browse(id_rubric)
                rub.unlink()
        return super(HrPayslipRubricConfig, self).unlink()

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
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
            if f not in ('id', 'sequence', 'code')
            if f not in groupby_fields
            if f in self._fields
            if self._fields[f].type in ('integer', 'float', 'monetary')
            if getattr(self._fields[f].base_field.column, '_classic_write', False)
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator or 'None',
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
    def get_rubric_conf_link(self):
        self.rubric_link = self.search([('rubric_link', '=', self.id)])

    @api.one
    def set_rubric_conf_link(self):
        self.rubric_link.rubric_link = self

    @api.multi
    def _create_rubric_link_rule(self):
        code_list = "max(%s)" % (','.join(self.mapped('rule_info_id.code')),)
        for rub in self:
            rub.with_context(from_link=True).write({'rubric_link_ids': [(6, 0, (self - rub).ids)]})
            amount_python_compute = """
result = %s%s if %s == %s else 0
				""" % (rub.mouvement, rub.rule_info_id.code, rub.rule_info_id.code, code_list)
            rub.rule_id.amount_python_compute = amount_python_compute

    @api.multi
    def _delete_rubric_link_rule(self):
        for rub in self:
            if not rub.is_readonly and rub.type in ('normal', 'fixe'):
                rub.with_context(from_link=True).write({'rubric_link_ids': [(6, 0, [])]})
                code_rule = 'INFO_' + str(rub.code)
                amount_python_compute_rule = """
result = ( %s%s or 0)
				""" % (rub.mouvement, code_rule)
                rub.rule_id.amount_python_compute = amount_python_compute_rule

    @api.model
    def get_sequence(self, rub_code):
        def try_int(code):
            try:
                return int(code)
            except ValueError:
                return False

        pre_code = rub_code[:2]
        su_code = rub_code[2:]
        if pre_code == "ST":
            result = 1100 + (try_int(su_code) or 99)
        elif pre_code == "SR":
            result = 1000 + (try_int(su_code) or 99)
        elif pre_code == "SC":
            result = 1200 + (try_int(su_code) or 99)
        else:
            result = try_int(rub_code) or 9999
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HrPayslipRubricConfig, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    @api.onchange('status')
    def dynamic_domain(self):
        domain = [(1, '=', 1)]
        if self.status == 'permanent':
            domain = [('status', '=', 'permanent')]
        elif self.status == 'journalier':
            domain = [('status', '=', 'journalier')]
        return {'domain': {'contract_ids': domain}}

    @api.one
    def onchange_status(self):
        contract_to_remove = []
        contract_to_add = []
        if not self.status:
            contract_to_remove = self.contract_ids

        elif self.status == 'journalier':
            contract_to_remove = self.contract_ids.filtered(lambda c: c.status != 'journalier')
            if self.classe_id.code in ['2', '5', '6', '8']:
                contract_to_add = self.env['hr.contract'].search([('status', '=', 'journalier')])

        elif self.status == 'permanent':
            contract_to_remove = self.contract_ids.filtered(lambda c: c.status != 'permanent')
            if self.classe_id.code in ['2', '5', '6', '8']:
                contract_to_add = self.env['hr.contract'].search([('status', '=', 'permanent')])

        elif self.status == 'mixte':
            if self.classe_id.code in ['2', '5', '6', '8']:
                contract_to_add = self.env['hr.contract'].search([('status', 'in', ['permanent', 'journalier'])])

        for contract in contract_to_remove:
            contract.variable_rubric_ids = [(3, self.id)]

        for contract in contract_to_add:
            contract.variable_rubric_ids = [(4, self.id)]

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrPayslipRubricConfig, self).fields_view_get(view_id, view_type, toolbar=toolbar,
                                                                    submenu=submenu)
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
        if not active_user.has_group('hr_copefrito_paie.group_pay_manager'):
            if view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        result['arch'] = etree.tostring(doc)
        return result

    @api.model
    def set_product_uom_name(self):
        self.env.ref('product.product_uom_hour').write({'name': 'h'})
        self.env.ref('product.product_uom_day').write({'name': 'j'})
        self.env.ref('product.product_uom_unit').write({'name': 'u'})
        print(self.env.ref('product.product_uom_hour') + self.env.ref('product.product_uom_day') + self.env.ref(
            'product.product_uom_unit')).mapped('name')


class ProductUom(models.Model):
    _inherit = 'product.uom'

    name = fields.Char('Unité de mesure', required=True, translate=False)
