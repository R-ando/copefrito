# -*- coding: utf-8 -*-

from openerp import models, api, fields, exceptions, _

class dirickx_xls_report(models.TransientModel):
    """docstring for xls_report"""
    _inherit = 'dirickx.xls.report'

    #hr_payslip_run = fields.Many2one('hr.payslip.run', u'Lots de bulletins de paie', required=True)

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO DOWNLOAD XLS REPORT
    @Author: Lanto R.
    @Begins on : 31/01/2017    
    __________________________________________________________________________________________

    """    

    @api.multi
    def get_dirickx_etat_paie_xls_file(self):
        return {
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_dirickx_xls_etat_paie_file?model=dirickx.xls.report&id=%s'%(self[0].id),
            'target': 'new',
        }   
