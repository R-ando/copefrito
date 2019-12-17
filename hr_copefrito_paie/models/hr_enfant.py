# -*- coding: utf-8 -*-

from openerp import models, api, fields
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


class hr_enfant(models.Model):
    _name = 'hr.enfant'
    _order = 'birthday desc'

    @api.depends('birthday')
    @api.multi
    def compute_age(self):
        """This function try to compute the age of
            Children from birthday field
        """
        for rec in self:
            if rec.birthday:
                now = date.today()
                birthday = datetime.strptime(rec.birthday, '%Y-%m-%d').date()
                complete_age = relativedelta(now, birthday)
                year = str(complete_age.years) + 'ans ' if complete_age.years > 0 else ''
                month = str(complete_age.months) + 'mois ' if complete_age.months > 0 else ''
                day = str(complete_age.days) + 'jours' if complete_age.days > 0 else ''
                rec.complete_age = year + month + day
                rec.age = complete_age.years

    name = fields.Char('Nom', size=256, required=True)
    birthday = fields.Date("Date de naissance", required=True)
    property_id = fields.Many2one('hr.employee', 'Employe', invisible=True)
    complete_age = fields.Char(compute='compute_age', string=u'Age Complet')
    allocation = fields.Boolean('Allocation')
    age = fields.Integer(compute='compute_age', string=u'Age')
    sexe = fields.Selection([('M', 'Masculin'), ('F', 'Feminin')], string=u'Genre')
