from openerp import api, models

class ResCountryInherit(models.Model):
    _inherit = 'res.country'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(ResCountryInherit, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
