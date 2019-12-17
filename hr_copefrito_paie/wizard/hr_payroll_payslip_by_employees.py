# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class hr_payslip_employees(osv.osv_memory):
    _inherit = 'hr.payslip.employees'
    
    
    def compute_sheet(self, cr, uid, ids, context=None):
        res = super(hr_payslip_employees,self).compute_sheet(cr, uid, ids, context)
        
        run_pool = self.pool.get('hr.payslip.run')
        class_pool = self.pool.get("hr.payslip.class")
        class_conf_pool = self.pool.get("hr.payslip.class.config")
        rubric_conf_pool = self.pool.get("hr.payslip.rubric.config")
        line_pool = self.pool.get('hr.payslip.line')
        rubric_pool = self.pool.get('hr.payslip.rubric')
        hpi_pool = self.pool.get('hr.payslip.input')
        
        rubric_ids = []
        class_ids = []
        rubric_list = []
        
        #update company_id for payslip
        run_data = None
        if context and context.get('active_id', False):
            run_data = run_pool.browse(cr, uid, [context['active_id']])
            for slip in run_data.slip_ids :
                slip.company_id = slip.employee_id.company_id
                slip.payment_mode = slip.employee_id.payment_mode
                for line in slip.line_ids :
                    if line.salary_rule_id.rubric_id :
                        rubric_ids.append(line.salary_rule_id.rubric_id.id)
                        class_ids.append(line.salary_rule_id.rubric_id.classe_id.id)
        
        #create class
        list_class = list(set(class_ids))
        for l in list_class:
            vals = {
                'payslip_run' : context['active_id'],
                'class_conf_id' : l,
            }
            class_pool.create(cr, uid, vals)
        
        # create rubric
        list_rubric = list(set(rubric_ids))
        for l in list_rubric :
            rubric_conf_obj = rubric_conf_pool.browse(cr, uid, l)
            class_id = class_pool.search(cr, uid, [('payslip_run', '=', context['active_id']), ('class_conf_id', '=', rubric_conf_obj.classe_id.id )] )
            vals = {
                'payslip_run' : context['active_id'],
                'paylip_rubric_conf_id' : l,
                'class_id' : class_id[0],
            }
            rubric_list.append(rubric_pool.create(cr, uid, vals))
            
        
        
        #get all lines in payslip
        line_ids = [] 
        for slip in run_data.slip_ids:
            for l in slip.line_ids : 
                line_ids.append(l.id)
            
        #update by rubric
        for rubric in rubric_list : 
            vals = {}
            rub_obj = rubric_pool.browse(cr, uid, rubric)
            if rub_obj.paylip_rubric_conf_id :
                payslip_line_rubric = line_pool.search(cr, uid, [('id', 'in',line_ids), ('salary_rule_id','=', rub_obj.paylip_rubric_conf_id.rule_id.id)])
                line_pool.write(cr, uid, payslip_line_rubric, {'rubric_id' : rubric})
                hpi_line_rubric = hpi_pool.search(cr, uid, [('payslip_id.payslip_run_id', '=', context['active_id']),('rule_id.rubric_id', '=', rub_obj.paylip_rubric_conf_id.id )])
                hpi_pool.write(cr, uid, hpi_line_rubric, {'rubric_id' : rubric} )
                if hpi_line_rubric == []: rub_obj.state = 'neutre'
                
        return res

