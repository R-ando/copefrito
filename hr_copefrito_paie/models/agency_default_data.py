
# -*- coding: utf-8 -*-

from openerp import models, api, fields


class agency_default_data(models.Model): ##-
    _name = 'agency.default.data'
    _description = 'Default data for agency'

    name = fields.Char('Code Agence',readonly=True)