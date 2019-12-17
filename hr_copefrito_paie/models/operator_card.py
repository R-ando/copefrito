# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.exceptions import ValidationError
from lxml import etree

class operator_card(models.Model):
    _name = 'operator.card'
    _sql_constraints = [
        ('operator_card_user_id_uniq', 
         'UNIQUE (user_id)', 
         'Employee must be unique')]
    
    responsable_employee_id = fields.Many2one('hr.employee', string=u'Employé', required=True)
    user_id = fields.Many2one('res.users', string=u'Employé', compute='compute_responsable_employee_id', store=True, readonly=True)
    rubric_ids = fields.Many2many('hr.payslip.rubric.config', string = u"Rubrique")
    company_id = fields.Many2one('res.company', string = u"Société", required=True)
    rubric_assigned = fields.Many2many('hr.payslip.rubric.config', string = u"Rubrique non disponible", compute="_compute_rubric_assigned")
    
    @api.model
    def create(self, vals):
        res = super(operator_card, self).create(vals)
        for rub in res.rubric_ids:
            rub.responsable_ids = [(4,res.user_id.id)]
        return res
    
    @api.multi
    def write(self, vals):
        old_rubric_ids = self.rubric_ids
        old_user_id = self.user_id
        res = super(operator_card, self).write(vals)
        
        for old_rub in old_rubric_ids:
            if old_rub not in old_rubric_ids.ids:
                old_rub.responsable_ids = [(3, old_user_id.id)]

        for rub in self.rubric_ids:
            rub.responsable_ids = [(3, old_user_id.id)]
            rub.responsable_ids = [(4, self.user_id.id)]
        
        return res

    @api.multi
    def unlink(self):
        for op in self:
            for rub in op.rubric_ids:
                rub.responsable_ids = [(3, op.user_id.id)]
        return super(operator_card, self).unlink()
    
    @api.one
    @api.depends('user_id', 'rubric_ids')
    def _compute_rubric_assigned(self):
        self.rubric_assigned = self.env['hr.payslip.rubric.config'].search([]).filtered(
            lambda rub: self.company_id.id not in [user_id.company_id.id for user_id in
                                                   rub.responsable_ids] if not rub.company_ids or self.company_id.id in rub.company_ids.ids else False)

    @api.onchange('rubric_assigned')
    def domain_onchange_rubric_assigned(self):
        if len(self.rubric_assigned) != 0:
            return {'domain': {'rubric_ids': [('id', 'in', self.rubric_assigned.ids)]}}
        else:
            return {'domain': {'rubric_ids': [('id', '=', 0)]}}
        

    @api.onchange('user_id')
    def onchange_user_id(self):
        self.company_id = self.user_id.company_id
        
    @api.onchange('company_id')
    def dynamic_domain(self):
        if self.company_id:
            return {'domain': {'user_id': [('company_id.id', '=', "%s" %self.company_id.id), ('id', 'in', self.env.ref('hr_copefrito_paie.group_pay_operateur').users.ids)]}}

    @api.depends('responsable_employee_id')
    def compute_responsable_employee_id(self):
        if self.responsable_employee_id:
            self.user_id = self.responsable_employee_id.user_id

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(operator_card, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
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