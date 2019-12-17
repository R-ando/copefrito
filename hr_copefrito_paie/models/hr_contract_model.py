# -*- coding: utf-8 -*-

from openerp import fields, models, api
from lxml import etree

class HrContractModel(models.Model):
    _name = 'hr.contract.model'

    name = fields.Char(string=u"Intitulés")
    code = fields.Char(string=u"Code")

    @api.onchange('code')
    def onchange_code(self):
        if self.code:
            self.code = str(self.code).upper()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrContractModel, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
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
