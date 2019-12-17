# -*- coding: utf-8 -*-

from datetime import datetime
from openerp import models, fields, _


class holiday_year(models.Model):
    _name = 'training.holiday.year'
    _rec_name = 'year'

    year = fields.Char('Year', size=64, select=1, required=True,
                       default=lambda *a: datetime.today().year)
    period_ids = fields.One2many('training.holiday.period',
                                 'year_id', 'Holiday Periods')

    _sql_constraints = [
        ('uniq_year', 'unique(year)', _('The year must be unique !')),
    ]
