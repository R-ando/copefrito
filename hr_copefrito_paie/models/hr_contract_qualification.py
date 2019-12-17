# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import ValidationError
from lxml import etree


class hr_contract_qualification(models.Model):
    _name = 'hr.contract.qualification'
    _description = 'Qualification contrat (ex : HC)'
    _order = 'name'

    name = fields.Char(string=u'Catégorie Professionnelle', size=64, required=True)
    note = fields.Text(string=u'Description')
    contract_qualification_ids = fields.One2many('hr.contract',
                                                 'contract_qualification_id',
                                                 string=u'Qualification')
    indice = fields.Integer(string=u'Indice')
    type = fields.Selection(string=u"Type",
                            selection=[('manager', 'Cadre'), ('employee', 'Employé'), ('worker', 'Ouvrier'),
                                       ('driver', 'Chauffeur'), ('daily', 'Journalier')])
    indice_duration = fields.Integer(string=u"Durée d'indice d'embauche")
    indice_seniority = fields.Integer(string=u"Indice ancienneté")
    is_hc = fields.Boolean(string=u"Est HC", compute='_compute_is_hc', store=True)

    @api.onchange('name')
    def set_capital_name(self):
        if self.name:
            capital_name = str(self.name).upper()
            self.name = capital_name

    @api.constrains('name')
    def _constrains_name_csp(self):
        if self.search([('name', '=', self.name)]) - self:
            raise ValidationError('Catégorie professionnelle déjà existante')

    @api.one
    @api.depends('type')
    def _compute_is_hc(self):
        if self.type == 'manager':
            self.is_hc = True
        else:
            self.is_hc = False

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(hr_contract_qualification, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
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