# -*- coding: utf-8 -*-

from openerp import api, models


class ResLangInherit(models.Model):
    _inherit = 'res.lang'

    @api.model
    def get_separator(self, code_lang):
        rec = self.search([('code', '=', code_lang)])
        return (rec.thousands_sep, rec.decimal_point)
