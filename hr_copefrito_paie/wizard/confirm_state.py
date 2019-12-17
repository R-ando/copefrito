# -*- coding: utf-8 -*-
from openerp import models, fields, api


class HrPayslipClassConfirm(models.TransientModel):
    _name = 'confirm.state'
    _description = u"Confirmation de refus"

    @api.multi
    def action_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model')

        self.env[active_model].browse(active_ids).set_inactive()

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_active(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model')

        self.env[active_model].browse(active_ids).set_active()

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_refresh(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model')

        self.env[active_model].browse(active_ids).refresh_base_salary()

        return {'type': 'ir.actions.act_window_close'}