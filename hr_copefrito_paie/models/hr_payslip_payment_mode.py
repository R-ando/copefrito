# -*- coding: utf-8 -*-

from openerp import models, fields

class hr_payslip_payment_mode(models.Model):

    _name = 'hr.payslip.payment.mode'
    _description = 'Mode de paiement(Virement, Cheque, ...)'

    name = fields.Char('Nom', size=256, required=True)
    note = fields.Text('Description')
    payslip_payment_mode_ids = fields.One2many('hr.contract',
                                               'payslip_payment_mode_id',
                                               'Mode de paiement')
    mobile = fields.Boolean('Mobile')
    payment_type = fields.Selection([('mobile', 'Mobile'), ('bank', 'Banque')], string=u"Type")

class hr_payslip_payment_mobile(models.Model):

    _name = 'hr.payslip.payment.mobile'
    _description = 'Type de paiement mobile'

    name = fields.Char('Nom', required=True)
    note = fields.Text('Description')