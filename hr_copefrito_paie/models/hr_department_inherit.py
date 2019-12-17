# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv

ALPHA = [chr(l).upper() for l in xrange(ord('a'), ord('z') + 1)]

def get_code_to_alpha(index):
    """
        this function convert an int to an alphanumeric code
        :example : 5 -> E, 27 -> AA
        :param index: int to convert to code
        :return: code
    """
    mod = (index % 26)
    div = int(index / 26)
    res = ALPHA[mod]
    if div > 0:
        res = ALPHA[div - 1] + res
    return res

class hr_department(models.Model):

    _inherit = 'hr.department'
    
    code_service = fields.Char('Code service', required = False)
    code = fields.Many2one('hr.code.service', string = "Code")
    
    @api.model
    def create(self, vals):        
        result = super(hr_department, self).create(vals)
        code_temp = {'name': result.code_service, 'service_id': result.id}
        result.code = self.env['hr.code.service'].create(code_temp)
        return result

    @api.multi
    def write(self, vals):
        result = super(hr_department, self).write(vals)
        code_temp = {'name': self.code_service, 'service_id': self.id}
        self.code.write(code_temp)
        return result

    @api.multi
    def unlink(self):
        self.env['hr.code.service'].search([('service_id', 'in', self.ids)]).unlink()
        return super(hr_department, self).unlink()

    @api.onchange('code_service')
    def set_capital_code_service(self):
        if self.code_service:
            capital_code = str(self.code_service).upper()
            self.code_service = capital_code

    @api.one
    def get_service_code(self):
        all_ids = self.search([], order="code_service asc").ids
        index = all_ids.index(self.id)
        return get_code_to_alpha(index)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(hr_department, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code_service', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

