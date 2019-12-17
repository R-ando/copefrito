# -*- coding: utf-8 -*-

from openerp import models, api, fields, exceptions


class HrContractAdvantage(models.Model):
    _name = 'hr.contract.advantage'
    _description = 'Manage employee advantage'

    name = fields.Char(string=u'Name', size=64)
    salary_rule_id = fields.Many2one('hr.salary.rule', string=u'Salary Rule',
                                     required=True)
    contract_id = fields.Many2one('hr.contract', string=u'Contract',
                                  required=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', string=u'Employee')
