# -*- coding: utf-8 -*-
from openerp import fields, api, models

class ResUsersInherit(models.Model):
    _inherit = 'res.users'

    service_ids = fields.Many2many('hr.department', string=u'Services autorisées')
    csp_ids = fields.Many2many('hr.contract.qualification', string=u"CSP autorisées")
    signature_img = fields.Binary("Signature")
