# -*- coding: utf-8 -*-

import cStringIO

from openerp import http
from openerp.addons.web.controllers.main import content_disposition, serialize_exception
from openerp.http import request
from openerp import api
import xlsxwriter
from datetime import datetime, date

from openerp import fields

import base64
from PIL import Image

import tempfile
import os

from collections import OrderedDict

from openerp.netsvc import logging
_logger = logging.getLogger(__name__)
 
schu=["","UN ","DEUX ","TROIS ","QUATRE ","CINQ ","SIX ","SEPT ","HUIT ","NEUF "]
schud=["DIX ","ONZE ","DOUZE ","TREIZE ","QUATORZE ","QUINZE ","SEIZE ","DIX SEPT ","DIX HUIT ","DIX NEUF "]
schd=["","DIX ","VINGT ","TRENTE ","QUARANTE ","CINQUANTE ","SOIXANTE ","SOIXANTE ","QUATRE VINGT ","QUATRE VINGT "]

class CopefritoXLSBinary(http.Controller):
	

	"""
	__________________________________________________________________________________________

	@Description : FUNCTION TO EXPORT XLS REPORT
	@Author: Sylvain Michel R.
	@Begins on : 12/12/2016
	@Latest update on : 27/12/2016
	__________________________________________________________________________________________

	"""    

	@http.route('/web/binary/download_copefrito_xls_file', type='http', auth="public")
	@serialize_exception
	def download_copefrito_xls_file(self, model, id, **args):  

		Model = request.registry[model]
		env, cr, uid, context = request.env, request.cr, request.uid, request.context
		copefrito_xls_report = Model.browse(cr, uid, int(id), context)[0]
		filename = "Ordre_de_paiement_%s.xlsx"%copefrito_xls_report.hr_payslip_run.name

		# info_recap = copefrito_xls_report.hr_payslip_run.get_info_recap()[0]

		file = cStringIO.StringIO()
		workbook = xlsxwriter.Workbook(file)

		title_style = workbook.add_format({'font_size':10, 'bold': True, 'italic': True, 'font_name': 'Calibri'})
		title_style_2 = workbook.add_format({'font_size':12, 'bold': True, 'font_name': 'Calibri', 'align': 'center'})
		title_style_3 = workbook.add_format({'font_size':10,  'font_name': 'Calibri'})
		title_style_4 = workbook.add_format({'font_size':12, 'bold': True,  'font_name': 'Calibri', 'underline': 'single'})
		title_style_5 = workbook.add_format({'font_size':11, 'bold': True, 'italic': True, 'font_name': 'Calibri'})
		title_style_6 = workbook.add_format({'font_size':10, 'font_name': 'Calibri', 'align': 'center'})
		amount_total_style = workbook.add_format({'font_size':9, 'bold': True, 'font_name': 'Calibri'})
		title_tab_style = workbook.add_format({'font_size':7, 'bold': True, 'font_name': 'Calibri', 'border':1, 'align': 'center', 'valign': 'vcenter', 'text_wrap':1})
		text_tab_style = workbook.add_format({'font_size':7, 'font_name': 'Calibri', 'border':1})
		text_tab_style_number = workbook.add_format({'font_size':7, 'font_name': 'Calibri', 'border':1, 'num_format':'#,##0.00'})
		text_tab_style_2 = workbook.add_format({'font_size':7, 'bold': True, 'font_name': 'Calibri', 'border':1})
		text_tab_style_2_number = workbook.add_format({'font_size':7, 'bold': True, 'font_name': 'Calibri', 'border':1, 'num_format':'#,##0.00'})
		text_tab_style_3 = workbook.add_format({'font_size':10, 'bold': True, 'font_name': 'Calibri', 'border':1})
		text_tab_style_3_number = workbook.add_format({'font_size':10, 'bold': True, 'font_name': 'Calibri', 'border':1, 'num_format':'#,##0.00'})
		text_tab_style_4 = workbook.add_format({'font_size':7, 'font_name': 'Calibri', 'border':1})
		text_tab_style_4_number = workbook.add_format({'font_size':7, 'font_name': 'Calibri', 'border':1, 'num_format':'#,##0.00'})


		cr.execute(""" SELECT 
			pl.id,
			pr.name AS lots,
			CASE
				WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
				ELSE CAST(emp.identification_cdi_id AS char)
			END AS matricule,  
			emp.name_related AS employee,
			emp.job_id,
			emp.bank_account_id,
			rpb.acc_number,
			rb.name AS bank_name,
			rb.bic,
			rpb.gab_code,
			rpb.acc_number,
			rpb.rib_key,            
			hpm.name AS payment_mode,
			pl.name AS name_code,
			pl.code AS code,
			pl.category_id,
			pl.quantity,
			pl.rate,
			pl.amount,
			pl.total
		FROM hr_payslip_run pr 
		LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
		LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
		LEFT JOIN hr_employee emp on emp.id=p.employee_id
		LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
		LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
		LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
		LEFT JOIN res_bank rb on rb.id=rpb.bank_id
		WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Virement' ORDER BY bank_name """,(copefrito_xls_report.hr_payslip_run.id,))

		result_bank = cr.dictfetchall()

		row_2 = total_virement = subtotal_amount = 0.0 

		if result_bank != []:

			# adding new tab named : "Virement"
			worksheet_virement = workbook.add_worksheet('Virement')

			# retrieving logo binary data
			hr_payslip_id = env['hr.payslip'].search([('payslip_run_id', '=', copefrito_xls_report.hr_payslip_run.id)], limit=1)

			logo_decoded_data = base64.decodestring(hr_payslip_id.company_id.logo)

			# create a temporary file, and save the image
			fobj = tempfile.NamedTemporaryFile(delete=False)
			fname = fobj.name
			print fname
			fname_new = fname.replace("\\","/").split("/") if '\\' in fname else fname.split("/")

			fname = ''
			fname_file = fname_new[len(fname_new)-1]
			for fn in range(len(fname_new)-1):
				fname += fname_new[fn] + '/'  

			fobj.write(logo_decoded_data)
			fobj.close()

			#Change the file extension for file in a folder to .jpg
			os.rename(fobj.name,fobj.name+'.jpg')

			#adding the image to the first tab of the xls file, at 'worksheet_virement' ("virement" tab)
			# Image.open(fname+fname_file+'.jpg').convert("RGB").resize((353, 88), Image.ANTIALIAS).save(fname+fname_file+'.jpg')
			Image.open(fname+fname_file+'.jpg').convert("RGB").resize((353, 88), Image.ANTIALIAS)
			worksheet_virement.insert_image(0,0,fname+fname_file+'.jpg')        

			worksheet_virement.set_column(0, 0, 15)
			worksheet_virement.set_column(1, 1, 7.5)
			worksheet_virement.set_column(2, 2, 7.5)
			worksheet_virement.set_column(3, 3, 10)
			worksheet_virement.set_column(4, 4, 5)       
			worksheet_virement.set_column(5, 5, 5)       
			worksheet_virement.set_column(6, 6, 35)       
			worksheet_virement.set_column(7, 7, 15)       
			worksheet_virement.set_column(8, 8, 15)

			rml_header1 = hr_payslip_id.company_id.rml_header1
			rcs = hr_payslip_id.company_id.company_registry
			stat = hr_payslip_id.company_id.stat
			street = hr_payslip_id.company_id.street
			street2 = hr_payslip_id.company_id.street2
			email = hr_payslip_id.company_id.email

			headers = OrderedDict([('rml_header1', rml_header1), ('rcs', rcs), ('stat', stat), ('street', street), ('street2', street2), ('email', email)])

			i = 7

			for header in headers:
				if headers[header] is not False:
					values = headers[header]
					if header == 'rml_header1':
						values = u'« ' + values + u' »'
					if header == 'stat':
						values = u'STAT : ' + str(values)
					if header == 'rcs':
						values = u'RCS : ' + str(values)
					worksheet_virement.merge_range('A%s:I%s'%(i, i), values, title_style)
					i += 1

			worksheet_virement.merge_range('A%s:I%s'%(i, i), 'ORDRE DE VIREMENT', title_style_2)
			worksheet_virement.merge_range('A%s:I%s'%(i+1, i+1), u'N/Réf : ' + copefrito_xls_report.hr_payslip_run.name, title_style_3)
			worksheet_virement.merge_range('A%s:I%s'%(i+2, i+2), u'Objet : ', title_style_4)
			worksheet_virement.merge_range('B%s:I%s'%(i+3, i+3), u'Salaires domicilié à la ', title_style_3)
			worksheet_virement.merge_range('B%s:I%s'%(i+4, i+4), u'Par le débit de notre compte N°: ', title_style_3)
			worksheet_virement.merge_range('B%s:I%s'%(i+5, i+5), u'Veuillez créditer les comptes suivants : ', title_style_5)      

			worksheet_virement.write(i+5,0, u'Banque', title_tab_style)
			worksheet_virement.write(i+5,1, u'Code Banque', title_tab_style)
			worksheet_virement.write(i+5,2, u'Code Guichet', title_tab_style)
			worksheet_virement.write(i+5,3, u'Numéro de Compte', title_tab_style)
			worksheet_virement.write(i+5,4, u'RIB', title_tab_style)
			worksheet_virement.write(i+5,5, u'Mat.', title_tab_style)
			worksheet_virement.write(i+5,6, u'Nom', title_tab_style)
			worksheet_virement.write(i+5,7, u'Net à payer', title_tab_style)
			worksheet_virement.write(i+5,8, u'Net à payer sans virgule', title_tab_style)    

			row = i+6

			current_bank_name = []

			for res_id in result_bank:
				current_bank_name.append(res_id['bank_name'])

			for current_bank in set(current_bank_name):
				for res in result_bank:
					if res['bank_name'] == current_bank:
						worksheet_virement.write(row,0, res['bank_name'], text_tab_style)
						worksheet_virement.write(row,1, res['bic'], text_tab_style)
						worksheet_virement.write(row,2, res['gab_code'], text_tab_style)
						worksheet_virement.write(row,3, res['acc_number'], text_tab_style)
						worksheet_virement.write(row,4, res['rib_key'], text_tab_style)
						worksheet_virement.write(row,5, res['matricule'], text_tab_style)
						worksheet_virement.write(row,6, res['employee'], text_tab_style)
						worksheet_virement.write_number(row,7, res['total'], text_tab_style_number)
						worksheet_virement.write_number(row,8, int(str(format(res['total'],'.2f')).replace('.','')), text_tab_style)

						subtotal_amount += res['total']
						row += 1
						row_2 += 1

				total_virement += subtotal_amount

				worksheet_virement.merge_range('A%s:G%s'%(row+1,row+1), 'TOTAL %s'%(current_bank), text_tab_style_2) if current_bank is not None \
				else worksheet_virement.merge_range('A%s:G%s'%(row+1,row+1), 'TOTAL' , text_tab_style_2)

				worksheet_virement.write_number(row,7, subtotal_amount, text_tab_style_2_number)
				worksheet_virement.write_number(row,8, int(str(format(subtotal_amount,'.2f')).replace('.','')), text_tab_style_2)

				subtotal_amount = 0
				row += 1
				row_2 += 1

			worksheet_virement.merge_range('A%s:G%s'%(row+1,row+1), 'TOTAL GENERAL', text_tab_style_2)            
			worksheet_virement.write_number(row,7, total_virement, text_tab_style_2_number)
			worksheet_virement.write_number(row,8, int(str(format(total_virement,'.2f')).replace('.','')), text_tab_style_2)

			worksheet_virement.merge_range('A%s:B%s'%(row+3,row+3), u'Arrêté la somme de : ')
			worksheet_virement.merge_range('C%s:I%s'%(row+3,row+3), convAmount(total_virement), amount_total_style)
			worksheet_virement.merge_range('A%s:I%s'%(row+5,row+5), u'Veuillez agréer Mesdames, Messieurs, nos salutations les meilleures.')

			# Get month of date today to avoid problem of unicode
			now = datetime.today().strftime('%B')

			fr_month = {'janvier': 'janvier','f\xe9vrier': u'février','mars': 'mars','avril': 'avril','mai': 'mai','juin': 'juin','juillet': 'juillet','ao\xfbt': u'août','septembre': 'septembre','octobre': 'octobre','novembre': 'novembre','d\xe9cembre': u'décembre'}       
			en_month = {'january': 'janvier','february': u'février','march': 'mars','april': 'avril','may': 'mai','june': 'juin','july': 'juillet','august': u'août','september': 'septembre','october': 'octobre','november': 'novembre','december': u'décembre'}

			# Re-incode month in unicode
			if now.lower() in fr_month:
				now = fr_month[now.lower()]
			if now.lower() in en_month:
				now = en_month[now.lower()]

			date_now = datetime.today()

			cr.execute('''SELECT EXTRACT(YEAR from (%s::date)) as annee,
								EXTRACT(MONTH from (%s::date)) as mois,
								EXTRACT(DAY from (%s::date)) as jours; ''',(date_now, date_now, date_now,))
			res = cr.fetchone()   
			date = str(int(res[2])) + ' ' + now + ' ' + str(int(res[0]))

			worksheet_virement.merge_range('A%s:I%s'%(row+7,row+7), u'Antananarivo le, %s'%(date), title_style_6)
			worksheet_virement.merge_range('A%s:I%s'%(row+9,row+9), u' Le Gérant', title_style_6)
			worksheet_virement.merge_range('A%s:I%s'%(row+10,row+10), env['res.users'].search([('id', '=', uid)]).name, title_style_6)

		cr.execute(""" SELECT
			CASE
				WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
				ELSE CAST(emp.identification_cdi_id AS char)
			END AS matricule,  
			emp.name_related AS employee,
			hpm.name AS payment_mode,
			ag.name AS agency_name,
			pl.total
		FROM hr_payslip_run pr 
		LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
		LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
		LEFT JOIN hr_employee emp on emp.id=p.employee_id
		LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
		LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
		LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
		LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
		LEFT JOIN res_bank rb on rb.id=rpb.bank_id
		WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Chèque' ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,))

		result_check = cr.dictfetchall()      

		row = 1
		row_2 = total_cheque = subtotal_amount = 0 

		current_agency_name = []

		if result_check != []:
			# adding new tab named : "Chèque"
			worksheet_cheque = workbook.add_worksheet(u'Chèque')

			worksheet_cheque.set_column(0, 0, 10)
			worksheet_cheque.set_column(1, 1, 35)
			worksheet_cheque.set_column(2, 2, 10)
			worksheet_cheque.set_column(3, 3, 20)        

			worksheet_cheque.write(0,0, u'Mat.', title_tab_style)
			worksheet_cheque.write(0,1, u'Nom', title_tab_style)
			worksheet_cheque.write(0,2, u'Agence', title_tab_style)
			worksheet_cheque.write(0,3, u'Net à payer', title_tab_style)


			for res_id in result_check:
				current_agency_name.append(res_id['agency_name'])

			for current_agency in set(current_agency_name):
				for res in result_check:
					if res['agency_name'] == current_agency:
						worksheet_cheque.write(row,0, res['matricule'], text_tab_style_4)
						worksheet_cheque.write(row,1, res['employee'], text_tab_style_4)
						worksheet_cheque.write(row,2, res['agency_name'], text_tab_style_4)
						worksheet_cheque.write_number(row,3, res['total'], text_tab_style_4_number)

						subtotal_amount += res['total']
						row += 1
						row_2 += 1

				total_cheque += subtotal_amount

				worksheet_cheque.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL %s'%(current_agency) , text_tab_style_3) if current_agency is not None \
				else worksheet_cheque.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL' , text_tab_style_3)

				worksheet_cheque.write_number(row,3, subtotal_amount, text_tab_style_3_number)

				subtotal_amount = 0
				row += 1
				row_2 += 1

			worksheet_cheque.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL GENERAL', text_tab_style_3)            
			worksheet_cheque.write_number(row,3, total_cheque, text_tab_style_3_number)


		# adding new tab named : "Chèque ###" e.g. : Chèque TNR

		total_cheque_details = {}

		for current_agency in set(current_agency_name):
			worksheet_cheque_details = workbook.add_worksheet(u'Chèque %s'%(current_agency))

			worksheet_cheque_details.set_column(0, 0, 10)
			worksheet_cheque_details.set_column(1, 1, 35)
			worksheet_cheque_details.set_column(2, 2, 10)
			worksheet_cheque_details.set_column(3, 3, 15)        
			worksheet_cheque_details.set_column(4, 4, 15)
			worksheet_cheque_details.set_column(5, 5, 20)

			worksheet_cheque_details.write(0,0, u'Mat.', title_tab_style)
			worksheet_cheque_details.write(0,1, u'Nom', title_tab_style)
			worksheet_cheque_details.write(0,2, u'Agence', title_tab_style)
			worksheet_cheque_details.write(0,3, u'Net à payer', title_tab_style)            
			worksheet_cheque_details.write(0,4, u'Numéro', title_tab_style)
			worksheet_cheque_details.write(0,5, u'Signature', title_tab_style)

			if current_agency is not None:
				cr.execute(""" SELECT
					CASE
						WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
						ELSE CAST(emp.identification_cdi_id AS char)
					END AS matricule,  
					emp.name_related AS employee,
					hpm.name AS payment_mode,
					ag.name AS agency_name,
					pl.total
				FROM hr_payslip_run pr 
				LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
				LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
				LEFT JOIN hr_employee emp on emp.id=p.employee_id
				LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
				LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
				LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
				LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
				LEFT JOIN res_bank rb on rb.id=rpb.bank_id
				WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Chèque' AND ag.name=%s ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,current_agency,))
			else:
			   cr.execute(""" SELECT
					CASE
						WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
						ELSE CAST(emp.identification_cdi_id AS char)
					END AS matricule,  
					emp.name_related AS employee,
					hpm.name AS payment_mode,
					ag.name AS agency_name,
					pl.total
				FROM hr_payslip_run pr 
				LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
				LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
				LEFT JOIN hr_employee emp on emp.id=p.employee_id
				LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
				LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
				LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
				LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
				LEFT JOIN res_bank rb on rb.id=rpb.bank_id
				WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Chèque' AND ag.name is null ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,))                

			result_check_details = cr.dictfetchall()

			row = 1
			row_2 = total_amount = 0 

			current_agency_name = []

			for res_id in result_check_details:
				current_agency_name.append(res_id['agency_name'])

			for current_agency in set(current_agency_name):
				for res in result_check_details:
					if res['agency_name'] == current_agency:
						worksheet_cheque_details.write(row,0, res['matricule'], text_tab_style_4)
						worksheet_cheque_details.write(row,1, res['employee'], text_tab_style_4)
						worksheet_cheque_details.write(row,2, res['agency_name'], text_tab_style_4)
						worksheet_cheque_details.write_number(row,3, res['total'], text_tab_style_4_number)
						worksheet_cheque_details.write(row,4, "", text_tab_style_4)
						worksheet_cheque_details.write(row,5, "", text_tab_style_4)

						total_amount += res['total']
						row += 1
						row_2 += 1

				total_cheque_details[res['agency_name']] = total_amount

				worksheet_cheque_details.merge_range('A%s:C%s'%(row+1,row+1), u'TOTAL Chèque %s'%(current_agency), text_tab_style_3) if current_agency is not None \
				else worksheet_cheque_details.merge_range('A%s:C%s'%(row+1,row+1), u'TOTAL Chèque' , text_tab_style_3)

				worksheet_cheque_details.write_number(row,3, total_amount, text_tab_style_3_number)
				worksheet_cheque_details.write(row,4, "", text_tab_style_3)
				worksheet_cheque_details.write(row,5, "", text_tab_style_3)

				total_amount = 0
				row += 1
				row_2 += 1

		cr.execute(""" SELECT
			CASE
				WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
				ELSE CAST(emp.identification_cdi_id AS char)
			END AS matricule,  
			emp.name_related AS employee,
			hpm.name AS payment_mode,
			ag.name AS agency_name,
			pl.total
		FROM hr_payslip_run pr 
		LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
		LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
		LEFT JOIN hr_employee emp on emp.id=p.employee_id
		LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
		LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
		LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
		LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
		LEFT JOIN res_bank rb on rb.id=rpb.bank_id
		WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Espèces' ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,))

		result_cash = cr.dictfetchall()

		row = 1
		row_2 = total_cash = subtotal_amount = 0 

		current_agency_name = []

		if result_cash != []:
			# adding new tab named : "Espèce"
			worksheet_cash= workbook.add_worksheet(u'Espèce')

			worksheet_cash.set_column(0, 0, 10)
			worksheet_cash.set_column(1, 1, 35)
			worksheet_cash.set_column(2, 2, 10)
			worksheet_cash.set_column(3, 3, 20)        

			worksheet_cash.write(0,0, u'Mat.', title_tab_style)
			worksheet_cash.write(0,1, u'Nom', title_tab_style)
			worksheet_cash.write(0,2, u'Agence', title_tab_style)
			worksheet_cash.write(0,3, u'Net à payer', title_tab_style)               


			for res_id in result_cash:
				current_agency_name.append(res_id['agency_name'])

			for current_agency in set(current_agency_name):
				for res in result_cash:
					if res['agency_name'] == current_agency:
						worksheet_cash.write(row,0, res['matricule'], text_tab_style_4)
						worksheet_cash.write(row,1, res['employee'], text_tab_style_4)
						worksheet_cash.write(row,2, res['agency_name'], text_tab_style_4)
						worksheet_cash.write_number(row,3, res['total'], text_tab_style_4_number)

						subtotal_amount += res['total']
						row += 1
						row_2 += 1

				total_cash += subtotal_amount

				worksheet_cash.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL %s'%(current_agency), text_tab_style_3) if current_agency is not None \
				else worksheet_cash.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL' , text_tab_style_3)

				worksheet_cash.write_number(row,3, subtotal_amount, text_tab_style_3_number)

				subtotal_amount = 0
				row += 1
				row_2 += 1

			worksheet_cash.merge_range('A%s:C%s'%(row+1,row+1), 'TOTAL GENERAL', text_tab_style_3)            
			worksheet_cash.write_number(row,3, total_cash, text_tab_style_3_number)


		# adding new tab named : "Espèce ###" e.g. : Espèce TNR

		total_cash_details = {}

		for current_agency in set(current_agency_name):
			worksheet_cash_details = workbook.add_worksheet(u'Espèce %s'%(current_agency))

			worksheet_cash_details.set_column(0, 0, 10)
			worksheet_cash_details.set_column(1, 1, 35)
			worksheet_cash_details.set_column(2, 2, 10)
			worksheet_cash_details.set_column(3, 3, 15)        
			worksheet_cash_details.set_column(4, 4, 15)
			worksheet_cash_details.set_column(5, 5, 20)

			worksheet_cash_details.write(0,0, u'Mat.', title_tab_style)
			worksheet_cash_details.write(0,1, u'Nom', title_tab_style)
			worksheet_cash_details.write(0,2, u'Agence', title_tab_style)
			worksheet_cash_details.write(0,3, u'Net à payer', title_tab_style)            
			worksheet_cash_details.write(0,4, u'Numéro', title_tab_style)
			worksheet_cash_details.write(0,5, u'Signature', title_tab_style)

			if current_agency is not None:
				cr.execute(""" SELECT
					CASE
						WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
						ELSE CAST(emp.identification_cdi_id AS char)
					END AS matricule,  
					emp.name_related AS employee,
					hpm.name AS payment_mode,
					ag.name AS agency_name,
					pl.total
				FROM hr_payslip_run pr 
				LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
				LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
				LEFT JOIN hr_employee emp on emp.id=p.employee_id
				LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
				LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
				LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
				LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
				LEFT JOIN res_bank rb on rb.id=rpb.bank_id
				WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Espèces' AND ag.name=%s ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,current_agency,))
			else:
				cr.execute(""" SELECT
					CASE
						WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
						ELSE CAST(emp.identification_cdi_id AS char)
					END AS matricule,  
					emp.name_related AS employee,
					hpm.name AS payment_mode,
					ag.name AS agency_name,
					pl.total
				FROM hr_payslip_run pr 
				LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
				LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
				LEFT JOIN hr_employee emp on emp.id=p.employee_id
				LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
				LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
				LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
				LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
				LEFT JOIN res_bank rb on rb.id=rpb.bank_id
				WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.name LIKE 'Espèces' AND ag.name is null ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,))


			result_cash_details = cr.dictfetchall()

			row = 1
			row_2 = total_amount = 0 

			current_agency_name = []

			for res_id in result_cash_details:
				current_agency_name.append(res_id['agency_name'])

			for current_agency in set(current_agency_name):
				for res in result_cash_details:
					if res['agency_name'] == current_agency:
						worksheet_cash_details.write(row,0, res['matricule'], text_tab_style_4)
						worksheet_cash_details.write(row,1, res['employee'], text_tab_style_4)
						worksheet_cash_details.write(row,2, res['agency_name'], text_tab_style_4)
						worksheet_cash_details.write_number(row,3, res['total'], text_tab_style_4_number)
						worksheet_cash_details.write(row,4, "", text_tab_style_4)
						worksheet_cash_details.write(row,5, "", text_tab_style_4)

						total_amount += res['total']
						row += 1
						row_2 += 1

				total_cash_details[res['agency_name']] = total_amount

				worksheet_cash_details.merge_range('A%s:C%s'%(row+1,row+1), u'TOTAL Espèce %s'%(current_agency), text_tab_style_3) if current_agency is not None \
				else worksheet_cash_details.merge_range('A%s:C%s'%(row+1,row+1), u'TOTAL Espèce' , text_tab_style_3)

				worksheet_cash_details.write_number(row,3, total_amount, text_tab_style_3_number)
				worksheet_cash_details.write(row,4, "", text_tab_style_3)
				worksheet_cash_details.write(row,5, "", text_tab_style_3)

				total_amount = 0
				row += 1
				row_2 += 1

		cr.execute(""" SELECT
		   CASE
				WHEN emp.identification_cdi_id='0' THEN (emp.identification_id)
				ELSE CAST(emp.identification_cdi_id AS char)
			END AS matricule,  
			emp.name_related AS employee,
			emp.tel_for_payment,
			hpm.name AS payment_mode,
			ag.name AS agency_name,
			pl.total
		FROM hr_payslip_run pr 
		LEFT JOIN hr_payslip p on pr.id=p.payslip_run_id
		LEFT JOIN hr_payslip_line pl on p.id=pl.slip_id
		LEFT JOIN hr_employee emp on emp.id=p.employee_id
		LEFT JOIN hr_contract hc on hc.employee_id=emp.id AND hc.id=p.contract_id
		LEFT JOIN hr_payslip_payment_mode hpm on hpm.id=(CASE WHEN p.payment_mode IS NOT NULL THEN p.payment_mode ELSE hc.payslip_payment_mode_id END)
		LEFT JOIN agency_default_data ag on ag.id=emp.agency_id
		LEFT JOIN res_partner_bank rpb on rpb.id=emp.bank_account_id
		LEFT JOIN res_bank rb on rb.id=rpb.bank_id
		WHERE code like 'NETAPAYER' AND p.payslip_run_id=%s AND hpm.mobile IS True ORDER BY agency_name """,(copefrito_xls_report.hr_payslip_run.id,))

		result_mobile_banking = cr.dictfetchall() 

		row = 1
		row_2 = total_mobile_banking = subtotal_amount = 0 

		total_mobile_details = {}

		if result_mobile_banking != []:

			current_mobile_name = []

			for res_id in result_mobile_banking:
				current_mobile_name.append(res_id['payment_mode'])         

			for current_mobile in set(current_mobile_name):
				
				# adding new tab named : "Mvola..."
				worksheet_mobile_banking= workbook.add_worksheet(current_mobile)
				worksheet_mobile_banking.set_column(0, 0, 10)
				worksheet_mobile_banking.set_column(1, 1, 35)
				worksheet_mobile_banking.set_column(2, 2, 20)
				worksheet_mobile_banking.set_column(3, 3, 15)        

				worksheet_mobile_banking.write(0,0, u'Mat.', title_tab_style)
				worksheet_mobile_banking.write(0,1, u'Nom', title_tab_style)
				worksheet_mobile_banking.write(0,2, u'Net à payer', title_tab_style)
				worksheet_mobile_banking.write(0,3, u'Téléphone', title_tab_style)               


				for res in result_mobile_banking:
					if res['payment_mode'] == current_mobile:

						worksheet_mobile_banking.write(row,0, res['matricule'], text_tab_style_4)
						worksheet_mobile_banking.write(row,1, res['employee'], text_tab_style_4)
						worksheet_mobile_banking.write_number(row,2, res['total'], text_tab_style_4_number)
						worksheet_mobile_banking.write(row,3, res['tel_for_payment'], text_tab_style_4)

						subtotal_amount += res['total']
						row += 1
						row_2 += 1

				worksheet_mobile_banking.merge_range('A%s:B%s'%(row+1,row+1), 'TOTAL' , text_tab_style_3)
				worksheet_mobile_banking.write_number(row,2, subtotal_amount, text_tab_style_3_number)              
				worksheet_mobile_banking.write(row,3, '', text_tab_style_3)

				total_mobile_details[current_mobile] = subtotal_amount                        
				
				total_mobile_banking += subtotal_amount

				row = 1
				row_2 = subtotal_amount = 0

		# adding new tab named : "Récapitulatif"
		worksheet_summary= workbook.add_worksheet(u'Récapitulatif')     

		worksheet_summary.set_column(0, 0, 25)
		worksheet_summary.set_column(1, 1, 25)        

		worksheet_summary.merge_range('A1:B1', u'ETAT RECAPITULATIF', title_tab_style)
		worksheet_summary.write(1,0, u'Rubriques', title_tab_style)
		worksheet_summary.write(1,1, u'Montants', title_tab_style)

		row = 2

		for tc in total_cheque_details:
			worksheet_summary.write(row,0, u'Chèque %s'%(tc), text_tab_style_4)
			worksheet_summary.write_number(row,1, total_cheque_details[tc], text_tab_style_4_number)
			row += 1

		worksheet_summary.write(row,0, u'Total Chèque', text_tab_style_3)
		worksheet_summary.write_number(row,1, total_cheque, text_tab_style_3_number)

		row += 1

		for tc in total_cash_details:
			worksheet_summary.write(row,0, u'Espèce %s'%(tc), text_tab_style_4)
			worksheet_summary.write_number(row,1, total_cash_details[tc], text_tab_style_4_number)
			row += 1        

		worksheet_summary.write(row,0, u'Total Espcèce', text_tab_style_3)
		worksheet_summary.write_number(row,1, total_cash, text_tab_style_3_number)

		row += 1

		worksheet_summary.write(row,0, 'Total Virement', text_tab_style_3)
		worksheet_summary.write_number(row,1, total_virement, text_tab_style_3_number)

		row += 1

		for tc in total_mobile_details:
			worksheet_summary.write(row,0, tc, text_tab_style_4)
			worksheet_summary.write_number(row,1, total_mobile_details[tc], text_tab_style_4_number)
			row += 1

		worksheet_summary.write(row,0, 'Total Mobile', text_tab_style_3)
		worksheet_summary.write_number(row,1, total_mobile_banking, text_tab_style_3_number)        

		row += 1

		total = total_virement + total_cash + total_cheque + total_mobile_banking

		worksheet_summary.write(row,0, 'TOTAL', text_tab_style_3)
		worksheet_summary.write_number(row,1, total, text_tab_style_3_number)         

		workbook.close() 
		if result_bank != []: os.unlink(fname+fname_file+'.jpg')       

		return request.make_response(file.getvalue(),
			[('Content-Type', 'application/octet-stream'),
			('Content-Disposition', content_disposition(filename))])


	@http.route('/web/binary/download_copefrito_xls_file_recap', type='http', auth="public")
	@serialize_exception
	def download_copefrito_xls_file_recap(self, model, id, **args):

		Model = request.registry[model]
		env, cr, uid, context = request.env, request.cr, request.uid, request.context
		copefrito_xls_report = Model.browse(cr, uid, int(id), context)[0]
		filename = u"Etat récapitulatif de la période de paie %s.xlsx" % copefrito_xls_report.hr_payslip_run.name

		file = cStringIO.StringIO()
		workbook = xlsxwriter.Workbook(file)

		col_head = workbook.add_format(
			{'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter',
			 'text_wrap': 1})
		company_name = workbook.add_format(
			{'font_size': 18, 'font_name': 'Calibri', 'font_color': '#0070d5', 'bold': True, 'align': 'center',
			 'valign': 'vcenter', 'text_wrap': 1})
		title = workbook.add_format(
			{'font_size': 14, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter',
			 'text_wrap': 1})
		period_label = workbook.add_format(
			{'font_size': 11, 'font_name': 'Calibri', 'align': 'right', 'valign': 'vcenter', })
		period_name = workbook.add_format(
			{'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'center',
			 'valign': 'vcenter', })
		simple_line_text = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'align': 'left'})
		simple_line_int = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'align': 'right'})
		simple_line_text_bold = workbook.add_format(
			{'font_size': 11, 'font_name': 'Calibri', 'border': 1, 'bold': True, 'align': 'left',
			 'bg_color': '#f2f2f2'})
		responsable_font = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'align': 'right'})
		direction_font = workbook.add_format({'font_size': 11, 'font_name': 'Calibri', 'align': 'center'})

		info_recap, payment_recap = copefrito_xls_report.hr_payslip_run.get_info_recap()[0]

		if info_recap:
			worksheet_cheque = workbook.add_worksheet(u'Recap')

			worksheet_cheque.set_column(0, 0, 1)
			worksheet_cheque.set_column(1, 1, 23)
			worksheet_cheque.set_column(2, 2, 8)
			worksheet_cheque.set_column(3, 3, 20)
			worksheet_cheque.set_column(4, 4, 14)
			worksheet_cheque.set_column(5, 5, 14)
			worksheet_cheque.set_column(6, 6, 16)
			worksheet_cheque.set_column(7, 7, 17)
			worksheet_cheque.set_column(8, 8, 15)
			worksheet_cheque.set_column(9, 9, 12)
			worksheet_cheque.set_column(10, 10, 12)
			worksheet_cheque.set_column(11, 11, 20)

			worksheet_cheque.write(1, 1, copefrito_xls_report.hr_payslip_run.company_id.name, company_name)
			worksheet_cheque.merge_range('D2:H2', u'ETAT RECAPITULATIF DE PAIE', title)
			worksheet_cheque.merge_range('I2:J2', u'Période de paie', period_label)
			worksheet_cheque.merge_range('K2:L2', copefrito_xls_report.hr_payslip_run.name, period_name)

			worksheet_cheque.write(3, 1, u'Services', col_head)
			worksheet_cheque.write(3, 2, u'Effectif', col_head)
			worksheet_cheque.write(3, 3, u'Salaire brut', col_head)
			worksheet_cheque.write(3, 4, u'CNAPS', col_head)
			worksheet_cheque.write(3, 5, u'OSIE', col_head)
			worksheet_cheque.write(3, 6, u'IRSA à payer', col_head)
			worksheet_cheque.write(3, 7, u'Retenues diverses', col_head)
			worksheet_cheque.write(3, 8, u'Allocation diverses', col_head)
			worksheet_cheque.write(3, 9, u'Ancien appoint', col_head)
			worksheet_cheque.write(3, 10, u'Nouvel appoint', col_head)
			worksheet_cheque.write(3, 11, u'Net à payer', col_head)

			l = 4
			for k in info_recap.keys():
				line = info_recap[k]
				worksheet_cheque.write(l, 1, line['name'], simple_line_text)
				worksheet_cheque.write(l, 2, abs(line['number']), simple_line_int)
				worksheet_cheque.write(l, 3, abs(line['gross']), simple_line_int)
				worksheet_cheque.write(l, 4, abs(line['cnaps']), simple_line_int)
				worksheet_cheque.write(l, 5, abs(line['ostie']), simple_line_int)
				worksheet_cheque.write(l, 6, abs(line['irsa']), simple_line_int)
				worksheet_cheque.write(l, 7, abs(line['retained']), simple_line_int)
				worksheet_cheque.write(l, 8, abs(line['allocation']), simple_line_int)
				worksheet_cheque.write(l, 9, abs(line['old_appoint']), simple_line_int)
				worksheet_cheque.write(l, 10, abs(line['new_appoint']), simple_line_int)
				worksheet_cheque.write(l, 11, abs(line['net_to_pay']), simple_line_int)
				l += 1

			get_sum = lambda dict, key: sum([dict[k][key] for k in dict.keys()])
			worksheet_cheque.write(l, 1, u'TOTAL', col_head)
			worksheet_cheque.write(l, 2, abs(get_sum(info_recap, 'number')), simple_line_int)
			worksheet_cheque.write(l, 3, abs(get_sum(info_recap, 'gross')), simple_line_int)
			worksheet_cheque.write(l, 4, abs(get_sum(info_recap, 'cnaps')), simple_line_int)
			worksheet_cheque.write(l, 5, abs(get_sum(info_recap, 'ostie')), simple_line_int)
			worksheet_cheque.write(l, 6, abs(get_sum(info_recap, 'irsa')), simple_line_int)
			worksheet_cheque.write(l, 7, abs(get_sum(info_recap, 'retained')), simple_line_int)
			worksheet_cheque.write(l, 8, abs(get_sum(info_recap, 'allocation')), simple_line_int)
			worksheet_cheque.write(l, 9, abs(get_sum(info_recap, 'old_appoint')), simple_line_int)
			worksheet_cheque.write(l, 10, abs(get_sum(info_recap, 'new_appoint')), simple_line_int)
			worksheet_cheque.write(l, 11, abs(get_sum(info_recap, 'net_to_pay')), simple_line_int)

			if payment_recap:

				l += 2
				commente = copefrito_xls_report.comment or " "
				worksheet_cheque.merge_range('B%s:D%s' % (l + 1, l + 1), u'BENEFICIAIRE DE PAIEMENT', col_head)
				worksheet_cheque.merge_range('F%s:H%s' % (l + 1, l + 1), u'A PAYER PAR', col_head)
				worksheet_cheque.insert_textbox(l, 8, "Commentaires:\n%s"%commente, {'x_scale': 2.2, 'y_scale': 1.5, 'x_offset': 10,
																		'border': {'color': 'black', 'width': 1}})
				worksheet_cheque.merge_range('I%s:J%s' % (l + 11, l + 11), u'Le Responsable de paie,', responsable_font)
				worksheet_cheque.merge_range('K%s:L%s' % (l + 11, l + 11), u'La direction,', direction_font)

				l += 2

				worksheet_cheque.write(l, 1, u'Mode de paiement', col_head)
				worksheet_cheque.write(l, 2, u'Effectif', col_head)
				worksheet_cheque.write(l, 3, u'Net à payer', col_head)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'Institution financière', col_head)
				worksheet_cheque.write(l, 7, u'Net à payer', col_head)

				l += 1

				transfer = payment_recap['transfer']
				worksheet_cheque.write(l, 1, u'Virement', simple_line_text_bold)
				worksheet_cheque.write(l, 2, u'', simple_line_text_bold)
				worksheet_cheque.write(l, 3, u'', simple_line_text_bold)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'Virement', simple_line_text_bold)
				worksheet_cheque.write(l, 7, u'', simple_line_text_bold)
				for bank in request.env['res.bank'].search([]):
					l += 1
					bank_info = transfer.get(bank.id)
					number, net_to_pay = (bank_info['number'], bank_info['net_to_pay']) if bank_info else (0, 0)
					worksheet_cheque.write(l, 1, bank.name, simple_line_text)
					worksheet_cheque.write(l, 2, number, simple_line_int)
					worksheet_cheque.write(l, 3, net_to_pay, simple_line_int)
					worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'', simple_line_text)
					worksheet_cheque.write(l, 7, u'', simple_line_int)

				l += 1

				mobile_bank = payment_recap['mobile']
				worksheet_cheque.write(l, 1, u'Mobile', simple_line_text_bold)
				worksheet_cheque.write(l, 2, u'', simple_line_text_bold)
				worksheet_cheque.write(l, 3, u'', simple_line_text_bold)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'Mobile', simple_line_text_bold)
				worksheet_cheque.write(l, 7, u'', simple_line_text_bold)
				for mobile in request.env['hr.payslip.payment.mobile'].search([]):
					l += 1
					mobile_info = mobile_bank.get(mobile.id)
					number, net_to_pay = (mobile_info['number'], mobile_info['net_to_pay']) if mobile_info else (0, 0)
					worksheet_cheque.write(l, 1, mobile.name, simple_line_text)
					worksheet_cheque.write(l, 2, number, simple_line_int)
					worksheet_cheque.write(l, 3, net_to_pay, simple_line_int)
					worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'', simple_line_int)
					worksheet_cheque.write(l, 7, u'', simple_line_int)

				l += 1
				cash = payment_recap['cash']
				worksheet_cheque.write(l, 1, u'Cash', simple_line_text_bold)
				worksheet_cheque.write(l, 2, u'', simple_line_text_bold)
				worksheet_cheque.write(l, 3, u'', simple_line_text_bold)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'Cash', simple_line_text_bold)
				worksheet_cheque.write(l, 7, u'', simple_line_text_bold)

				l += 1
				number, net_to_pay = (cash[0]['number'], cash[0]['net_to_pay']) if cash.get(0) else (0, 0)
				worksheet_cheque.write(l, 1, u'Cash', simple_line_text)
				worksheet_cheque.write(l, 2, number, simple_line_int)
				worksheet_cheque.write(l, 3, net_to_pay, simple_line_int)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'', simple_line_text)
				worksheet_cheque.write(l, 7, u'', simple_line_int)

				l += 1
				worksheet_cheque.write(l, 1, u'TOTAL', col_head)
				worksheet_cheque.write(l, 2, get_sum(info_recap, 'number'), simple_line_int)
				worksheet_cheque.write(l, 3, get_sum(info_recap, 'net_to_pay'), simple_line_int)
				worksheet_cheque.merge_range('F%s:G%s' % (l + 1, l + 1), u'TOTAL', col_head)
				worksheet_cheque.write(l, 7, u'', simple_line_int)


		workbook.close()

		return request.make_response(file.getvalue(),
									 [('Content-Type', 'application/octet-stream'),
									  ('Content-Disposition', content_disposition(filename))])


def convAmount(nombre):
	reste_apres_virgule =  (nombre - int(nombre))*100
	return str(convNumber2letters(nombre)) + 'Ariary ' + str(convNumber2letters(round(reste_apres_virgule))).lower()

def convNumber2letters(nombre):
	s=''
	reste=int(nombre)

	i=1000000000 
	while i>0:
		y=reste/i
		if y!=0:
			centaine=y/100
			dizaine=(y - centaine*100)/10
			unite=y-centaine*100-dizaine*10
			if centaine==1:
				s+="CENT "
			elif centaine!=0:
				s+=schu[centaine]+"CENT "
				if dizaine==0 and unite==0: s=s[:-1]+"S " 
			if dizaine not in [0,1]: s+=schd[dizaine] 
			if unite==0:
				if dizaine in [1,7,9]: s+="DIX "
				elif dizaine==8: s=s[:-1]+"S "
			elif unite==1:   
				if dizaine in [1,9]: s+="ONZE "
				elif dizaine==7: s+="ET ONZE "
				elif dizaine in [2,3,4,5,6]: s+="ET UN "
				elif dizaine in [0,8]: s+="UN "
			elif unite in [2,3,4,5,6,7,8,9]: 
				if dizaine in [1,7,9]: s+=schud[unite] 
				else:
					if nombre < 9: s+='ZERO ' + schu[unite] 
					else: s+=schu[unite] 
			if i==1000000000:
				if y>1: s+="MILLIARDS "
				else: s+="MILLIARD "
			if i==1000000:
				if y>1: s+="MILLIONS "
				else: s+="MILLION "
			if i==1000:
				s+="MILLE "
		reste -= y*i
		dix=False
		i/=1000;
	return s.capitalize()

from openerp import http
from openerp.http import request
import werkzeug.utils

class CopefritoMailController(http.Controller):

	@http.route('/web/disable/<int:id>', auth='user', type='http', methods=['GET','POST'], website=True, csrf=False)
	def cancel_url(self, id):
		contract = http.request.env['hr.contract'].browse(id)
		contract.enable_notifications = False
		action_id = http.request.env.ref('hr_contract.hr_menu_contract').action.id
		menu_id = http.request.env.ref('hr_contract.hr_menu_contract').id
		url_request = 'web?db=%s#id=%s&view_type=form&model=hr.contract&action=%s&menu_id=%s' % (
			http.request._cr.dbname, contract.id, action_id, menu_id)
		return werkzeug.utils.redirect(url_request)



