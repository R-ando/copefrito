# -*- coding: utf-8 -*-

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import models, api, fields, exceptions, _
from openerp.exceptions import UserError


class HrPrimeTypeWiz(models.TransientModel):
    _name = 'hr.prime.type.wiz'
    _description = """Wizard who allow you to generate
    prime in contract"""
    
    contract_ids = fields.Many2many("hr.contract", "hr_contract_prime_typ_rel", 'prim_type_id', 'contract_id', string=u"Contrats")
    
    @api.multi
    def action_apply(self):
        prime_type_id = self.env.context.get('active_id', False)
        prime_type_obj = self.env['hr.prime.type'].browse(prime_type_id)
        
        if prime_type_id and prime_type_obj.primetype == 'prime':
            for contract in self.contract_ids:
                prime_ids = contract.prime_ids.filtered(lambda r: r.prime_type_id.id == prime_type_id)
                
                # if prime already exists, update values prime
                if prime_ids:
                    vals = {
                        'amount' : prime_type_obj.amount,
                        'prorata' : prime_type_obj.prorata
                    }
                    prime_ids.write(vals)
                # create new prime for the contract
                else :
                    vals = {
                        'prime_type_id' : prime_type_id,
                        'contract_id'  : contract.id,
                        'amount' : prime_type_obj.amount,
                        'prorata' : prime_type_obj.prorata
                    }
                    self.env['hr.contract.prime'].create(vals)
                    
            contract_ids = prime_type_obj.contract_ids + self.contract_ids
            prime_type_obj.contract_ids = contract_ids
        
        elif prime_type_id and prime_type_obj.primetype == 'avantage':
            for contract in self.contract_ids:
                benefit_ids = contract.benefit_ids.filtered(lambda r: r.prime_type_id.id == prime_type_id)
                
                # if benefit already exists, update values prime
                if benefit_ids:
                    vals = {
                        'amount' : prime_type_obj.amount,
                        'prorata' : prime_type_obj.prorata
                    }
                    benefit_ids.write(vals)
                # create new benefit for the contract
                else :
                    vals = {
                        'prime_type_id' : prime_type_id,
                        'contract_id_benefit'  : contract.id,
                        'amount' : prime_type_obj.amount,
                        'prorata' : prime_type_obj.prorata
                    }
                    self.env['hr.contract.prime'].create(vals)
                    
            contract_ids = prime_type_obj.contract_ids + self.contract_ids
            prime_type_obj.contract_ids = contract_ids

        return {'type': 'ir.actions.act_window_close'}

