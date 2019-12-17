# -*- encoding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import rrule

from openerp import models, api, fields, _
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT as DT_FORMAT


class holiday_year_wizard(models.TransientModel):
    _name = 'training.holiday.year.wizard'
    _description = 'Generate week'

    year = fields.Integer('Year', required=True,
                          default=lambda *a: datetime.today().year)

    @api.multi
    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_apply(self):
        holiday_year_obj = self.env['training.holiday.year']
        holiday_period_obj = self.env['training.holiday.period']
        holiday_categ = self.env['training.holidays.category']
        categ = holiday_categ.search([('name', '=', 'Week-End')], limit=1)
        if not categ:
            categ = holiday_categ.create({'name': 'Week-End'})
        wizard = self
        try:
            year_start = datetime.strptime('%04s-01-01' % (wizard.year,),
                                           DT_FORMAT)
            year_end = datetime.strptime('%04s-12-31' % (wizard.year,),
                                         DT_FORMAT)
        except:
            raise ValueError(_('Please enter valid year'))

        year_id = holiday_year_obj.create({'year': wizard.year})

        # Generate holiday periods for each week-end of requested year
        # NOTE: we use ISO week number, but if the 1st saturday of the
        #       year is before the 1st thursday we force week-num to 0
        year_rule = rrule.rrule(rrule.DAILY, dtstart=year_start,
                                until=year_end, byweekday=(rrule.SA))
        for saturday in year_rule:
            iso_year, iso_weeknum, iso_weekday = saturday.isocalendar()
            weeknum = iso_year == wizard.year and iso_weeknum or 0
            date_stop = (saturday+relativedelta(days=1)).strftime(DT_FORMAT)
            vals_period = {
                'year_id': year_id.id,
                'date_start': saturday.strftime(DT_FORMAT),
                'date_stop': date_stop,
                'name': _('Week-End %02d') % weeknum,
                'categ': categ.id,
            }
            holiday_period_obj.create(vals_period)

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'training.holiday.year',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': year_id.id,
        }

    @api.model
    def action_apply_scheduler(self):
        holiday_year_obj = self.env['training.holiday.year']
        holiday_period_obj = self.env['training.holiday.period']
        holiday_categ = self.env['training.holidays.category']
        categ = holiday_categ.search([('name', '=', 'Week-End')])
        if not categ:
            cat = holiday_categ.create({'name': 'Week-End'})
            categ = holiday_categ.browse([cat])
        date = datetime.now()
        year = date.strftime("%Y")
        year = int(year)
        year += 1
        try:
            year_start = datetime.strptime('%04s-01-01' % (year,), DT_FORMAT)
            year_end = datetime.strptime('%04s-12-31' % (year,), DT_FORMAT)
        except:
            raise ValueError(_('Please enter valid year'))

        year_id = holiday_year_obj.create({'year': year})

        # Generate holiday periods for each week-end of requested year
        # NOTE: we use ISO week number, but if the 1st saturday of the
        #       year is before the 1st thursday we force week-num to 0
        year_rule = rrule.rrule(rrule.DAILY, dtstart=year_start,
                                until=year_end, byweekday=(rrule.SA))
        for saturday in year_rule:
            iso_year, iso_weeknum, iso_weekday = saturday.isocalendar()
            weeknum = iso_year == year and iso_weeknum or 0
            date_stop = (saturday+relativedelta(days=1)).strftime(DT_FORMAT)
            holiday_period_obj.create({
                'year_id': year_id,
                'date_start': saturday.strftime(DT_FORMAT),
                'date_stop': date_stop,
                'name': _('Week-End %02d') % (weeknum,),
                'categ': categ[0],
            }),

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
