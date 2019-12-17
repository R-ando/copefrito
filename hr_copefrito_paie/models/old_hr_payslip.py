#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import api, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp


from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

class hr_payslip(osv.osv):
	_inherit= "hr.payslip"

	def _get_lines_salary_rule_category(self, cr, uid, ids, field_names, arg=None, context=None):
		result = {}
		if not ids: return result
		for id in ids:
			result.setdefault(id, [])
		cr.execute('''SELECT pl.slip_id, pl.id FROM hr_payslip_line AS pl \
					LEFT JOIN hr_salary_rule_category AS sh on (pl.category_id = sh.id) \
					WHERE pl.slip_id in %s AND pl.active is true\
					GROUP BY pl.slip_id, pl.sequence, pl.id ORDER BY pl.sequence''',(tuple(ids),))
		res = cr.fetchall()
		for r in res:
			result[r[0]].append(r[1])
		return result

	_columns = {
		'details_by_salary_rule_category': fields.function(_get_lines_salary_rule_category, method=True, type='one2many', relation='hr.payslip.line', string='Details by Salary Rule Category'),
	}


	
  
