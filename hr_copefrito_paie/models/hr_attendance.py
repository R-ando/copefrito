# -*- coding: utf-8 -*-

from openerp import models, api, fields


class hr_attendance(models.Model):
    _inherit = 'hr.attendance'

    parent_id = fields.Many2one('hr.attendance', compute='_get_sign_in',
                                string=u'Sign In')
    parent_name = fields.Datetime(string=u'sign in', related='parent_id.name', store=True)

    @api.multi
    @api.depends('employee_id', 'action')
    def _get_sign_in(self):
        for rec in self:
            if rec.employee_id and rec.action == 'sign_out':
                parent_id = rec.search([('employee_id', '=', rec.employee_id.id),
                                        ('action', '=', 'sign_in'),
                                        ('name', '<', rec.name)],
                                       order='name DESC', limit=1)
                rec.parent_id = parent_id.id
