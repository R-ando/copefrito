# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, api, fields, exceptions, _
from openerp.exceptions import UserError


class hr_timesheet_sheet_wizard(models.TransientModel):

    """
    This wizard will confirm the all the selected confirmed sheet
    """

    _name = 'hr.timesheet.sheet.wizard'
    _description = "Confirm the selected sheet"

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO APPROVE SELECTED CONFIRMED SHEET
    @Author: Sylvain Michel R.
    @Begins on : 22/12/2016
    @Latest update on : 26/12/2016
    __________________________________________________________________________________________

    """    

    @api.multi
    def sheet_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['hr_timesheet_sheet.sheet'].browse(active_ids):
            if record.state not in ('confirm', 'done'):
                raise UserError(_("Les feuilles de temps sélectionnées ne peuvent pas être approuvées car elles n'ont pas encore été confirmées."))
            if record.state in ('done'):
                raise UserError(_("Les feuilles de temps sélectionnées sont déjà approuvées."))
            record.signal_workflow('done')
        return {'type': 'ir.actions.act_window_close'}