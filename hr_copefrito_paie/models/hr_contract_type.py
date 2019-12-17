# -*- coding: utf-8 -*-

from openerp import models, api, fields, exceptions


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    code = fields.Char(string=u'Code', help='Code will be used on programming')
    
    _rec_name = 'code'
