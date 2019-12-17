# -*- coding: utf-8 -*-

from openerp import models, api, fields
from lxml import etree
from openerp.osv.orm import setup_modifiers

def restrict_right(doc, view_type):
    if view_type == 'tree':
        for node in doc.xpath('//tree'):
            node.set('create', 'false')
            node.set('delete', 'false')
    elif view_type == 'form':
        for node in doc.xpath('//form'):
            node.set('edit', 'false')
    return doc

def del_key(dic, key):
    try:
        del dic[key]
    except KeyError:
        pass

class HrPayrollStructureInherit(models.Model):

    _inherit = 'hr.payroll.structure'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrPayrollStructureInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            result['arch'] = etree.tostring(doc)
        return result

class HrSalaryRuleCategoryInherit(models.Model):

    _inherit = 'hr.salary.rule.category'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrSalaryRuleCategoryInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            result['arch'] = etree.tostring(doc)
        return result

class HrSalaryRuleInherit(models.Model):

    _inherit = 'hr.salary.rule'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrSalaryRuleInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            result['arch'] = etree.tostring(doc)
        return result

class HrContributionRegisterInherit(models.Model):

    _inherit = 'hr.contribution.register'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrContributionRegisterInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            result['arch'] = etree.tostring(doc)
        return result

class ResGroupsInherit(models.Model):

    _inherit = 'res.groups'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ResGroupsInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            result['arch'] = etree.tostring(doc)
        return result

class ResUsersInherit(models.Model):

    _inherit = 'res.users'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ResUsersInherit, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            doc = restrict_right(doc, view_type)
            if view_type == 'form':
                for node in doc.xpath("//header//button"):
                    # should delete the key state because it raise a bug in "def transfer_field_to_modifiers(field, modifiers):"
                    # in openerp/osv/orm.py line: 38
                    if 'states' in node.attrib:
                        del (node.attrib['states'])
                    node.set('invisible', '1')
                    # node.set('invisible', '1') is not applied even if we don't call set_up_modifiers
                    setup_modifiers(node, node.attrib)
            # del_key(result, 'toolbar')
            if result.get('toolbar') and result.get('toolbar').get('action'):
                result['toolbar'].update({'action': []})
            result['arch'] = etree.tostring(doc)
        return result