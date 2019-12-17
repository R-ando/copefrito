# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, api, fields, exceptions, _
from openerp.exceptions import UserError


class HrTimesheetWiz(models.TransientModel):
    _name = 'hr.timesheet.wiz'
    _description = """Wizard who allow you to generate
    monthly timesheet"""

    @api.model
    def _default_date_start(self):
        user = self.env['res.users'].browse(self._uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return time.strftime('%Y-%m-01')
        elif r=='week':
            return (datetime.today() + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-01-01')
        return fields.date.context_today()

    @api.model
    def _default_date_stop(self):
        user = self.env['res.users'].browse(self._uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return (datetime.today() + relativedelta(months=+1,day=1,days=-1)).strftime('%Y-%m-%d')
        elif r=='week':
            return (datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-12-31')
        return fields.date.context_today()

    date_start = fields.Date(string=u'Date start', required=True, default=_default_date_start, help='Date Start')
    date_stop = fields.Date(string=u'Date stop', required=True, default=_default_date_stop, help='Date Stop')
    employee_ids = fields.Many2many('hr.employee', string=u'Employee',
                                    help='List of Employee will own timesheet sheet')

    @api.multi
    def action_apply(self):
        timesheet_obj = self.env['hr_timesheet_sheet.sheet']
        if not self.date_start or not self.date_stop:
            raise UserError(_("Please Insert correct date !"))
        elif self.date_start >= self.date_stop:
            raise UserError(_("Start date should be older than Stop date !"))
        else:
            # all is correct we can process
            if not self.employee_ids:
                raise UserError(_("You should at least insert 1 employee !"))
            else:
                for employee in self.employee_ids:
                    if not employee.user_id:
                        raise UserError(_("Please, define an user for employee: %s !") % (employee.name,))
                    else:
                        vals = {'employee_id': employee.id,
                                'date_from': self.date_start,
                                'date_to': self.date_stop}
                        timesheet_obj.create(vals)

        return {
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'hr_timesheet_sheet.sheet',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': False,
        }

