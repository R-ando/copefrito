# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp import tools
from lxml import etree
from datetime import datetime


class hr_payslip_input_vs_line(models.Model):
    _name = "hr.payslip.input.vs.line"
    _auto = False

    payslip_run_id = fields.Many2one('hr.payslip.run', string=u"Période de paie")
    payslip_id = fields.Many2one('hr.payslip', string=u"Bulletin de paie")
    rubric_id = fields.Many2one('hr.payslip.rubric.config', string=u"Rubrique")
    input_amount = fields.Float(string=u"Entrée")
    line_amount = fields.Float(string=u"Calculé")
    period_date = fields.Date(string=u"Date")
    employee_id = fields.Many2one('hr.employee', string=u'Nom et prénom(s)')
    matricule = fields.Char('Matricule')
    birthday = fields.Date(u'Date de naissance')
    num_cnaps = fields.Char(u'N° CNAPS')
    num_cin = fields.Char(u'N° CIN')
    date_cin = fields.Date(u'Date de délivrance CIN')
    gender = fields.Selection([('male', 'Masculin'), ('female', u'Féminin'), ('other', 'Autre')], string="Sexe")
    date_start = fields.Date(string=u'Date d\'embauche')
    date_end = fields.Date(string=u'Date de débauche')
    job_id = fields.Many2one('hr.job', string=u'Poste')
    department_id = fields.Many2one('hr.department', string=u'Service')
    address_bis_id = fields.Char('Addresse')
    csp = fields.Many2one('hr.contract.qualification', string='CSP')
    indice = fields.Integer(string=u'Indice utilisé')
    point_indice_val = fields.Float(u'Valeur des points d\'indice')
    num_contract = fields.Char(string=u"N° Contrat", required=False)
    status = fields.Selection([('permanent', 'Permanent'), ('journalier', 'Journalier'), ('stagiaire', 'Stagiaire'),
                               ('visiteur', 'Visiteur')], string=u'Statut', default='permanent')
    payment_mode = fields.Many2one('hr.payslip.payment.mode', u'Mode de paiement')
    payment_mobile = fields.Many2one('hr.payslip.payment.mobile', string=u"Mobile banking")
    bank_account_id = fields.Many2one('res.partner.bank', 'Bank Account Number', help="Employee bank salary account")
    tel_for_payment = fields.Char('Payment Phone Number')
    bank_name = fields.Char('Bank Name')

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'hr_payslip_input_vs_line')
        cr.execute("""
            CREATE or REPLACE view hr_payslip_input_vs_line AS
                SELECT
                    ROW_NUMBER() OVER (ORDER BY req.id) AS id,
                    req.payslip_id,
                    req.payslip_run_id,
                    req.rubric_id,
                    sum(req.input_amount) AS input_amount,
                    sum(req.line_amount) AS line_amount,
                    req.period_date,
                    req.employee_id,
                    req.matricule,
                    req.birthday,
                    req.num_cnaps,
                    req.num_cin,
                    req.date_cin,
                    req.gender,
                    req.address,
                    req.date_start,
                    req.date_end,
                    req.job_id,
                    req.department_id,
                    req.csp,
                    req.indice,
                    req.num_contract,
                    req.status,                    
                    req.point_indice_val,
                    req.payment_mode,
                    req.payment_mobile,
                    req.bank_account_id,
                    req.tel_for_payment,
                    req.bank_name                    
                FROM (
                    SELECT
                        hpl.id AS id,
                        hp.id AS payslip_id,
                        hprn.id AS payslip_run_id,
                        hprc.id AS rubric_id,
                        CASE 
                            WHEN hprc.id IS NOT NULL THEN hpi.amount
                            ELSE 0
                        END AS input_amount,
                        0 as line_amount,
                        hprn.date_end AS period_date,
                        he.id AS employee_id,
                        he.identification_cdi_id AS matricule,
                        he.birthday AS birthday,
                        he.num_cnaps AS num_cnaps,
                        he.num_cin AS num_cin,
                        he.date_cin AS date_cin,
                        he.gender AS gender,
                        he.address_bis_id AS address,
                        hrc.date_start AS date_start,
                        hrc.date_end AS date_end,
                        hrc.job_id AS job_id,
                        hrc.department_id AS department_id,
                        hrc.contract_qualification_id AS csp,
                        hrc.indice AS indice,
                        hrc.num_contract,
                        hrc.status,
                        pti.amount AS point_indice_val,
                        hp.payment_mode,
                        hp.payment_mobile,
                        hp.bank_account_id,
                        hp.tel_for_payment,
                        rb.name AS bank_name
                    FROM hr_payslip_rubric hpr
                    LEFT JOIN hr_payslip_rubric_config hprc ON hprc.id=hpr.paylip_rubric_conf_id
                    LEFT JOIN hr_payslip_input hpi ON hpi.rubric_id=hpr.id
                    LEFT JOIN hr_payslip_run hprn ON hprn.id=hpr.payslip_run
                    LEFT JOIN hr_payslip hp ON hp.id=hpi.payslip_id
                    LEFT JOIN hr_payslip_line hpl ON hpl.rubric_id=hpr.id AND hpl.slip_id=hp.id AND hpl.appears_on_payslip is true
                    LEFT JOIN hr_employee he ON he.id=hp.employee_id
                    LEFT JOIN hr_contract hrc ON hrc.id=hp.contract_id
                    LEFT JOIN point_indice pti ON pti.id=hrc.point_indice
                    LEFT JOIN res_partner_bank rpb on rpb.id=hp.bank_account_id
                    LEFT JOIN res_bank rb ON rb.id=rpb.bank_id
                    WHERE hp.state != 'cancel'
                    UNION ALL
                    SELECT
                        hpl.id,
                        hp.id AS payslip_id,
                        hprn.id AS payslip_run_id,
                        hprc.id AS rubric_id,
                        0 as input_amount,
                        hpl.amount AS line_amount,
                        hprn.date_end AS period_date,
                        he.id AS employee_id,
                        he.identification_cdi_id AS matricule,
                        he.birthday AS birthday,
                        he.num_cnaps AS num_cnaps,
                        he.num_cin AS num_cin,
                        he.date_cin AS date_cin,
                        he.gender AS gender,
                        he.address_bis_id AS address,
                        hrc.date_start AS date_start,
                        hrc.date_end AS date_end,
                        hrc.job_id AS job_id,
                        hrc.department_id AS department_id,
                        hrc.contract_qualification_id AS csp,
                        hrc.indice AS indice,
                        hrc.num_contract,
                        hrc.status,                        
                        pti.amount AS point_indice_val,                        
                        hp.payment_mode,
                        hp.payment_mobile,
                        hp.bank_account_id,
                        hp.tel_for_payment,
                        rb.name as bank_name                      
                    FROM hr_payslip_line as hpl
                    LEFT JOIN hr_payslip hp ON hp.id=hpl.slip_id
                    LEFT JOIN hr_employee he ON he.id=hp.employee_id
                    LEFT JOIN hr_contract hrc ON hrc.id=hp.contract_id
                    LEFT JOIN point_indice pti ON pti.id=hrc.point_indice
                    LEFT JOIN hr_payslip_run hprn ON hprn.id=hp.payslip_run_id
                    LEFT JOIN hr_payslip_rubric hpr on hpr.id=hpl.rubric_id
                    LEFT JOIN hr_payslip_rubric_config hprc on hprc.id=hpr.paylip_rubric_conf_id
                    LEFT JOIN res_partner_bank rpb on rpb.id=hp.bank_account_id
                    LEFT JOIN res_bank rb ON rb.id=rpb.bank_id
                    WHERE  
                    hpl.appears_on_payslip is true and hp.state != 'cancel'
                    ) AS req 
                    WHERE req.payslip_id is not null and req.payslip_run_id is not null and req.rubric_id is not null
                    GROUP BY
                        req.id,
                        req.payslip_id,
                        req.payslip_run_id,
                        req.rubric_id,
                        req.period_date,
                        req.employee_id,
                        req.matricule,
                        req.birthday,
                        req.num_cnaps,
                        req.num_cin,
                        req.date_cin,
                        req.gender,
                        req.address,
                        req.date_start,
                        req.date_end,
                        req.job_id,
                        req.department_id,
                        req.csp,
                        req.indice,
                        req.num_contract,
                        req.status,                          
                        req.point_indice_val,
                        req.payment_mode,
                        req.payment_mobile,
                        req.bank_account_id,
                        req.tel_for_payment,
                        req.bank_name  
        """)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(hr_payslip_input_vs_line, self).fields_view_get(view_id, view_type, toolbar=toolbar,
                                                                       submenu=submenu)
        doc = etree.XML(result['arch'])
        if view_type == 'search':
            # last_period  = self.env['hr.payslip.run'].search([('state', '=', 'validate')], order="date_start desc", limit=1)
            last_period = self.env['hr.payslip.run'].search([], order="date_end desc", limit=1)
            if last_period:
                str_month = ['Janvier', u'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', u'Août', 'Septembre',
                             'Octobre', 'Novembre', u'Décembre']
                ref_date = last_period.date_end
                domain = "[('period_date', '=', '%s')]" % ref_date
                ref_date_date = datetime.strptime(ref_date, "%Y-%m-%d")
                name = "%s %s" % (str_month[ref_date_date.month - 1], ref_date_date.year)
                for node in doc.xpath("//filter[@name='filter_last_month']"):
                    node.set('domain', domain)
                    node.set('string', name)
                result['arch'] = etree.tostring(doc)
        return result

    @api.v7
    def open_hr_payslip_analysis_pivot(self, cr, uid, ids, context):
        user = self.pool.get('res.users').browse(cr, uid, uid)
        domain = []
        if not user.has_group('hr_copefrito_paie.group_pay_manager') and not user.has_group(
                'hr_copefrito_paie.group_direction'):
            if user.has_group('hr_copefrito_paie.group_pay_operateur'):
                domain += ['|', ('payslip_id.contract_id.is_hc', '=', False),
                           ('payslip_id.contract_id.contract_qualification_id', '=', False)]
            elif user.has_group('hr_copefrito_paie.group_service_manager'):
                domain += [('payslip_id.contract_id.department_id', 'in', user.service_ids.ids),
                           ('payslip_id.contract_id.contract_qualification_id', 'in', user.csp_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': u'Etat nominatif de salaire',
            'res_model': 'hr.payslip.input.vs.line',
            'view_type': 'form',
            'view_mode': 'pivot',
            'domain': domain,
            'context': "{'search_default_filter_last_month':1}"
        }
