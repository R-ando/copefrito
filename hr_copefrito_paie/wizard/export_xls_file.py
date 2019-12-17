# -*- coding: utf-8 -*-

from openerp import models, api, fields, exceptions, _

class copefrito_xls_report(models.TransientModel):
    """docstring for xls_report"""
    _name = 'copefrito.xls.report'

    hr_payslip_run = fields.Many2one('hr.payslip.run', u'Lots de bulletins de paie')

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO DOWNLOAD XLS REPORT
    @Author: Sylvain Michel R.
    @Begins on : 12/12/2016
    @Latest update on : 19/12/2016
    __________________________________________________________________________________________

    """    

    @api.multi
    def get_copefrito_xls_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_copefrito_xls_file?model=copefrito.xls.report&id=%s'%(self[0].id),
            'target': 'new',
        }

class copefrito_xls_report_recap(models.TransientModel):
    """docstring for xls_report"""
    _name = 'copefrito.xls.report.recap'

    hr_payslip_run = fields.Many2one('hr.payslip.run', u'Lots de bulletins de paie')
    comment = fields.Text(u'Commentaires')

    @api.multi
    def get_copefrito_xls_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_copefrito_xls_file_recap?model=copefrito.xls.report.recap&id=%s'%(self[0].id),
            'target': 'new',
        }
