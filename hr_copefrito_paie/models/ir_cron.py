# -*- coding: utf-8 -*-

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import models, api, fields
from openerp.netsvc import logging

_logger = logging.getLogger(__name__)

class ir_cron(models.Model):

	_inherit = 'ir.cron'
	

	@api.one
	def _name_get(self):
		res = {}
		for record in self:
			name = record.name

			if record.function=="auto_increment_remaining_leaves":
				name = name + ('  (%s)' % (self.date2word(record.nextcall) or ''))
			else:
				name = name

		# res[record.id] = name
		self.name_with_date = name
		
		return True

	@api.multi
	def date2word(self, date):

		date = str(date)

		annee = mois = ''
		self.env.cr.execute('''SELECT EXTRACT(YEAR from (%s::date)) as annee,
							EXTRACT(MONTH from (%s::date)) as mois; ''',(date, date,))
		res = self.env.cr.fetchone()

		return str(self.convert_month_to_french_string(int(res[1])) + " " + str(int(res[0])))

	@api.multi
	def convert_month_to_french_string(self, mounth_id):
		str_month = ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre']

		return str_month[int(mounth_id-1)]

	@api.model
	def auto_increment_remaining_leaves(self):
		obj_holy = self.env['hr.holidays']
		obj_company = self.env['res.company']
		obj_emp = self.env['hr.employee']
		
		_logger.info('Start auto-increment remaining leaves')
				
		nb_solde_mensuelle = 2.5
		for conge in obj_company.search([('conge_mens','!=', '')],limit=1):
			nb_solde_mensuelle = conge.conge_mens

		try:
			leave_ids = []        
			for emp in obj_emp.search([]):
				category_names = []
				if len(emp.category_ids) > 0:
					for category in emp.category_ids:
						category_names.append(category.name)

					if 'employe' in category_names and 'conge_maternite' not in category_names:
						vals = {
							'type': 'add',
							'holiday_type': 'employee',
							'holiday_status_id': 1,
							'notes': 'Attribution de 2.5 jours de congé par mois',
							'employee_id': emp.id,
							'date_from': datetime.now()
						}

						if emp.id:
							if emp.job_id.hol_per_month == 0:
								vals['number_of_days_temp'] = 2.5
								vals['name'] = 'Attribution de 2.5 jours de congé par mois'
								vals['notes'] = 'Attribution de 2.5 jours de congé par mois'
							else:
								vals['number_of_days_temp'] = emp.job_id.hol_per_month
								vals['name'] = "Attribution de %s jours de congé par mois" % (emp.job_id.hol_per_month)
								vals['notes'] = "Attribution de %s jours de congé par mois" % (emp.job_id.hol_per_month)
							leave_ids.append(obj_holy.create(vals))
							print "----------------------------------------------------"
							print "Cron du %s Employee id %s" % (datetime.now(), emp.id)
							print "----------------------------------------------------"
			
			for leave_id in leave_ids:
				obj_holy.search([('id', '=', leave_id.id)]).write({'state':'validate'})            


			_logger.info('Validated')
			_logger.info('End auto-increment remaining leaves')
		except:
			_logger.info('Erreur')

		return True




	name_with_date = fields.Char(compute='_name_get', string=u"Nom", store=False)
	
	