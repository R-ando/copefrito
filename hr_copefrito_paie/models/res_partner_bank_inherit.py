# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import osv
from lxml import etree

class ResPartnerBank(models.Model):
	_inherit = "res.partner.bank"

	"""
	FOR CREATING NEW ACCOUNT BANK
	"""


	@api.model
	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		result = super(ResPartnerBank, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
		doc = etree.XML(result['arch'])
		if view_type == 'form':
			employees = self.search([]).mapped('employee_id').ids
			domain = "[('id', 'not in', %s)]" %employees
			for node in doc.xpath("//field[@name='employee_id']"):
				node.set('domain', domain)

		result['arch'] = etree.tostring(doc)
		return result
 
	@api.model
	def create(self, vals):
		acc_number = vals.get('acc_number', False)
		rib_key = vals.get('rib_key', False)
		gab_code = vals.get('gab_code', False)
		bank_id = vals.get('bank_id', False)

		# test "Numéro de compte"
		if acc_number == False or len(acc_number) != 11 or self.isNumber(acc_number) == False:
			raise osv.except_osv(u'OUPS!', u'Le numéro de compte bancaire n\'est pas constistué de 11 chiffres')

		# test "code guichet"
		if gab_code == False or len(gab_code) != 5 or self.isNumber(gab_code) == False:
			raise osv.except_osv(u'OUPS!', u'Le code guichet n\'est pas constistué de 5 chiffres')

		# test "Clé RIB"
		if rib_key == False or len(rib_key) != 2 or self.isNumber(rib_key) == False:
			raise osv.except_osv(u'OUPS!', u'La clé RIB n\'est pas constistué de 2 chiffres')

		if self.search(['&', ('acc_number', '=', acc_number), ('bank_id', '=', bank_id)]):
			raise osv.except_osv(u'OUPS!', u'Le numéro de compte bancaire d\'une même banque doit être unique')

		return super(ResPartnerBank, self).create(vals)

	"""
	FOR EDITING EXISTING ACCOUNT BANK
	"""

	# 
	@api.multi
	def write(self, vals):
		for rec in self:
			acc_number = vals.get('acc_number', rec.acc_number)
			rib_key = vals.get('rib_key', False)
			gab_code = vals.get('gab_code', False)
			bank_id = vals.get('bank_id', rec.bank_id.id)

			# test "Numéro de compte"
			if acc_number != rec.acc_number and acc_number != False:  # so the acc_number field has changed
				if len(acc_number) != 11 or rec.isNumber(acc_number) == False:
					raise osv.except_osv(u'OUPS!', u'Le numéro de compte bancaire n\'est pas constistué de 11 chiffres')
			if acc_number == False and rec.acc_number != False:  # have NOT changed
				if len(rec.acc_number) != 11 or rec.isNumber(rec.acc_number) == False:
					raise osv.except_osv(u'OUPS!', u'Le numéro de compte bancaire n\'est pas constistué de 11 chiffres!')

			# test "code guichet"
			if gab_code != rec.gab_code and gab_code != False:  # so the gab_code field has changed
				if len(gab_code) != 5:
					raise osv.except_osv(u'OUPS!', u'Le code guichet n\'est pas constistué de 5 chiffres')

			if gab_code != False and rec.isNumber(gab_code) == False:  # have changed
				raise osv.except_osv(u'OUPS!', u'Le code guichet contient autre que des chiffres')

			if gab_code == False and rec.gab_code != False:  # have NOT changed
				if len(rec.gab_code) != 5:
					raise osv.except_osv(u'OUPS!', u'Le code guichet n\'est pas constistué de 5 chiffres!')

			# test "Clé RIB"
			if rib_key != rec.rib_key and rib_key != False:  # so the gab_code field has changed
				if len(rib_key) != 2:
					raise osv.except_osv(u'OUPS!', u'La clé RIB n\'est pas constistué de 2 chiffres')

			if rib_key != False and rec.isNumber(rib_key) == False:  # have changed
				raise osv.except_osv(u'OUPS!', u'La clé RIB contient autre que des chiffres')

			if rib_key == False and rec.rib_key != False:  # have not changed
				if len(rec.rib_key) != 2:
					raise osv.except_osv(u'OUPS!', u'La clé RIB n\'est pas constistué de 2 chiffres')

			if rec.search(['&', ('acc_number', '=', acc_number), ('bank_id', '=', bank_id)]):
				raise osv.except_osv(u'OUPS!', u'Le numéro de compte bancaire d\'une même banque doit être unique')

		return super(ResPartnerBank, self).write(vals)

	def isNumber(self, Chaine):
		"""
		@def: Test si une chaine de caractere contient un chiffre positif        
		@param Chaine: chaine à tester
		@author : Lanto
		@type Chaine: texte
		@return: boolean
		@rtype: boolean
		"""
		res = False
		chiffre = "0123456789"
		i = 0
		sCh = str(Chaine)
		while (i < len(sCh)):
			if (sCh[i] in chiffre):
				res = True
			else:
				return False
			i = i + 1
		return res

	
	acc_number = fields.Char('Account Number', size=11, required=True)
	gab_code = fields.Char(u"Code Guichet", size=5, required=True)
	# final_bank_account_code = fields.Char(u"Numéro de compte")
	rib_key = fields.Char(u"Clé RIB", size=2, required=True)
	bank_id = fields.Many2one('res.bank', string=u'Bank', required=True)
	company_id = fields.Many2one('res.company', u'Société', default=False, ondelete='cascade')
	employee_id = fields.Many2one('hr.employee', string=u"Employé titulaire de compte")
	
	#remove native _sql_constraints
	_sql_constraints = [
		('unique_number', 'Check(1=1)', 'Account Number must be unique'),
	]

class ResBankInherit(models.Model):
	_inherit = 'res.bank'

	@api.model
	def name_search(self, name='', args=None, operator='ilike', limit=100):
		if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
			return super(ResBankInherit, self).name_search(name, args, operator, limit)
		args = args or []
		domain = [('bic', operator, name)]
		recs = self.search(domain + args, limit=limit)
		return recs.name_get()
	#remove native _sql_constraints
	_sql_constraints = [
		('unique_number', 'Check(1=1)', 'Account Number must be unique'),
	]
	#remove native _sql_constraints
	_sql_constraints = [
		('unique_number', 'Check(1=1)', 'Account Number must be unique'),
	]


