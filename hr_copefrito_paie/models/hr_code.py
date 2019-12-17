# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools
from openerp.tools.translate import _
from openerp.exceptions import ValidationError


class hr_code_poste(models.Model):
    _name = 'hr.code.poste'
    _sql_constraints = [
        ('hr_code_name_uniq', 'UNIQUE (name)', 'Le nom doit être unique'),
        ('hr_code_job_id_uniq', 'UNIQUE (job_id)', 'Le poste doit être unique')
    ]
    
    name = fields.Char('Code')
    job_id = fields.Many2one('hr.job', string = "Poste")
    
class hr_code_service(models.Model):
    _name = 'hr.code.service'
    _sql_constraints = [
        ('hr_code_name_uniq', 'UNIQUE (name)', 'Le nom doit être unique'),
        ('hr_code_service_id_uniq', 'UNIQUE (service_id)', 'Le service doit être unique')
    ]
    
    name = fields.Char('Code')
    service_id = fields.Many2one('hr.department', string = "Service")