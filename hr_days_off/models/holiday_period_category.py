# -*- coding: utf-8 -*-
from openerp import models, fields


class holiday_period_category(models.Model):
    _name = 'training.holidays.category'
    name = fields.Char('Name', size=128, required=True)
