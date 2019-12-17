# -*- coding: utf-8 -*-

from openerp import models, api, fields, exceptions
import openerp.addons.decimal_precision as dp

Payroll = dp.get_precision('Payroll')


class ResOrganismeMedical(models.Model):
    _name = 'res.organisme.medical'
    _description = 'Manage company medical organism'

    name = fields.Char(string=u'Nom de l\'organisme', size=64)
    plafond_organisme = fields.Float(u'Plafond', digits_compute=Payroll)
    taux_salarial = fields.Float(u'Taux salarial (%)', digits_compute=Payroll)
    taux_patronal = fields.Float(u'Taux patronal (%)', digits_compute=Payroll)
    company_id = fields.Many2one('res.company', string=u'Société')

    _rec_name = 'name'