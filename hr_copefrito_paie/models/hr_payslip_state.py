# -*- coding: utf-8 -*-

from openerp import models, api, fields


class hr_payslip_state(models.Model):
    _name = 'hr.payslip.state'
    
    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Recruitment Pipe')
    done = fields.Boolean('Request Done')