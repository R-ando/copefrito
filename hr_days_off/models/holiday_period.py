# -*- coding: utf-8 -*-
import time
from openerp import models, api, fields, _
from openerp.exceptions import ValidationError
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT as DT_FORMAT
import datetime
from datetime import timedelta, datetime, date


class holiday_period(models.Model):
    _name = 'training.holiday.period'

    year_id = fields.Many2one('training.holiday.year', 'Year', required=True,
                              ondelete='cascade')
    name = fields.Char('Name', size=64, required=True)
    date_start = fields.Date('Date Start', required=True,
                             default=lambda *a: time.strftime(DT_FORMAT))
    date_stop = fields.Date('Date Stop', required=True,
                            default=lambda *a: time.strftime(DT_FORMAT))
    active = fields.Boolean('Active', default=lambda *a: 1)
    categ = fields.Many2one('training.holidays.category', 'Category')

    @api.one
    @api.constrains('date_start', 'date_stop')
    def _check_date_start_stop(self):
        if self.date_start > self.date_stop:
            raise ValidationError(_('Please, check the start date !'))
        return True

    @api.cr
    def is_in_period(self, date):
        if not date:
            raise ValueError(_('''no date specified for
                               'is in period' holiday period check'''))
        cr = self._cr
        cr.execute("SELECT count(id) "
                   "FROM training_holiday_period "
                   "WHERE %s BETWEEN date_start AND date_stop AND active='1'",
                   (date,))
        return cr.fetchone()[0] > 0

    @api.model
    def get_nb_days(self, date_start, date_end):
        diff_date = lambda d1, d2: (datetime.strptime(str(d2), "%Y-%m-%d") - (
            datetime.strptime(str(d1), "%Y-%m-%d"))).days + 1

        nb_dayoff = 0
        include_days = self.search([('date_start', '>=', date_start), ('date_stop', '<=', date_end)])
        if include_days:
            nb_dayoff += sum([diff_date(d.date_start, d.date_stop) for d in include_days])
        begin_days = self.search(
            [('date_start', '<', date_start), ('date_stop', '>=', date_start), ('date_stop', '<', date_end)], limit=1)
        if begin_days:
            nb_dayoff += diff_date(date_start, begin_days.date_stop)
        end_days = self.search(
            [('date_start', '<=', date_end), ('date_stop', '>', date_end), ('date_start', '>', date_start)], limit=1)
        if end_days:
            nb_dayoff += diff_date(end_days.date_start, date_end)
        return nb_dayoff
