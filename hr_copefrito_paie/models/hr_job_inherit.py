# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv
from openerp.exceptions import ValidationError

class hr_job(models.Model):

    _inherit = 'hr.job'
    _rec_name = 'name'
    
    name =  fields.Char('Poste', required=True, select=True, translate=False)
    code_poste = fields.Char('Code poste', required = False)
    hol_per_month = fields.Float(u'Nombre de congés par mois', default = 2.5)
    service_id = fields.Many2one('hr.department', string=u"Service", required=True)
    code = fields.Many2one('hr.code.poste', string = "Code")
    code_service = fields.Char('Code service', related='service_id.code_service', store=True)

    @api.constrains('hol_per_month')
    def _constrains_hol_per_month(self):
        if self.hol_per_month >=31:
            raise ValidationError('Le nombre de congés ne doit pas excéder de 31 jours')

    @api.model
    def create(self, vals):
        result = super(hr_job, self).create(vals)
        name = result.code_poste or False
        job_id = result.code.job_id or False
        code_temp = {'name': name, 'job_id': job_id}
        result.code = self.env['hr.code.poste'].create(code_temp)
        return result

    @api.multi
    def write(self, vals):
        result = super(hr_job, self).write(vals)
        code_temp = {'name': self.code_poste, 'job_id': self.id}
        self.code.write(code_temp)
        return result

    @api.multi
    def unlink(self):
        self.env['hr.code.poste'].search([('job_id', 'in', self.ids)]).unlink()
        return super(hr_job, self).unlink()

    @api.onchange('code_poste')
    def set_capital_code_poste(self):
        if self.code_poste:
            capital_code = str(self.code_poste).upper()
            self.code_poste = capital_code

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(hr_job, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code_poste', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'hol_per_month' in fields:
            fields.remove('hol_per_month')
        return super(hr_job, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
