# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv
from datetime import datetime
    
class HrHolidaysStatusInherit(models.Model):
    _inherit = 'hr.holidays.status'
    
    deductible = fields.Boolean(u'Déductible', default=True)
    
class HrHolidaysInherit(models.Model):
    _inherit = 'hr.holidays'
    
    addhalfday = fields.Boolean(u'+ une demi-journée', default = False)
    halfdayposition = fields.Selection([
                                      ('before', 'Au début du congé'),
                                      ('after', 'A la fin du congé')
                                      ],
                                     string=u'Position')
    deductible_type = fields.Boolean(related='holiday_status_id.deductible',string = u'Déductible')
    visible_payslip = fields.Boolean(u'Ne pas afficher dans le bulletin')
    
    @api.onchange('number_of_days_temp')
    def onchange_number_of_days_temp(self):
        n = (self.number_of_days_temp*2)%2
        if n == 0:
            self.addhalfday = False
            self.halfdayposition = False
        else:
            self.number_of_days_temp = float(int(self.number_of_days_temp))-0.5            
            self.addhalfday = True
            self.halfdayposition = 'after'

    def holidays_validate(self, cr, uid, ids, context=None):
        res = super(HrHolidaysInherit, self).holidays_validate(cr, uid, ids, context=context)
        vals = {'date_from': datetime.now()}
        if self.browse(cr, uid, ids)[0].type == 'add': self.write(cr, uid, ids[0], vals)        
        return res            
        