# -*- coding: utf-8 -*-

{
    "name": 'Copefrito - Gestion de la Paie',
    'version': '0.1',
    'category': 'Others',
    'sequence': 150,
    'summary': "",
    "description": u"""Copefrito Payroll Rules.
    ======================

       Gestion de la Paie Malagasy:
        - Gestion des employés :
            * Type de contrat,
            * Modes de paiement
        - Gestion des contrats
        - Gestion des congés :
            * Attribution automatique de 2.5 jours de congés par mois pour chaque employé,
        - Gestion des feuilles de temps :
            * Récupération automatique des heures travaillées pour chaque employé,
            * Calcul automatique des heures supplémentaires, heures sur dimanche, heures sur jours fériés et heures nuits
        - Gestion de la paie :
            * Calcul automatique des entrées : heures supplémentaires, heures sur dimanche, heures sur jours fériés, heures nuits, congés non déductibles, allocation familliale et déduction pour enfant
            * Calcul automatique de la prime d'ancienneté, heures supplémentaires, cotisations salariales et patronales, ...
            * Calcul automatique des congés déductibles/non déductibles
        - Comptabilisation de la paie : configuration des comptes de credit et de débit
        - Reporting : bulletins de paie, reçus stagiaire, ordre de paiement au format .xlsx
        - Configuration et paramètrage
            * Les rubriques de paie : primes, indemnités, avantages, déductions, ...
            * Les rubriques cotisables, imposable, soumise à la prime d'ancienneté  ...
            * Les cotisations : cotisations salariales et patronales CNAPS, Mutuelle...
            * Barème de la prime d'ancienneté, cotisations CNAPS, ...

    """,
    "version": "0.1",
    "depends": [
        'base',
        'hr',
        'hr_attendance',
        'hr_timesheet_sheet',
        # 'product',
        'hr_contract',
        'hr_payroll',
        'web',
        'hr_days_off',
        'board',
        'web_no_database_manager',
        'document',
        # 'model_history',
        'report_qweb_element_page_visibility',
        'dispaly_many2one_link',
        'bus',
        'web',
        'decimal_precision',
        'mail'
		
    ],
    "author": "Sylvain Michel R., Ny Zo R., Samuel R. - Etech Madagascar",
    "category": "Others",
    "installable": True,
    "data": [
        'data/category_group.xml',
        'data/security_group.xml',
        'data/security_rule.xml',
        'data/hr_holidays_status_data.xml',
        'data/res_company_data.xml',
        'data/account_analytic_account_data.xml',
        'data/hr_payroll_workflow.xml',
        'data/resource_calendar_records.xml',
        'data/resource_calendar_attendance_records.xml',
        'data/hr_employee_agency_data.xml',
        'data/hr_employee_status_type.xml',
        'data/hr_department_data.xml',
        # 'data/hr_employee_function.xml',
        'data/monthly_hours_contract_data.xml',
        'data/hr_payslip_payment_mode_data.xml',
#         'data/timesheet_cron_data.xml',
#         'data/type_log_cron_data.xml',
        'data/hr_contract_type_data.xml',
        'data/hr_payroll_data.xml',
        # 'data/rubric_data.xml',
        'data/hr_payslip_class_config_data.xml',
        'data/hr_payslip_rubric_config_data.xml',
        'data/hr_payslip_state_data.xml',
        'data/hr_contract_data.xml',
        'data/set_fr_lang.yml',
        'data/ir_cron_data.xml',
        # 'data/update_rubric.yml',
        'data/set_email_partner.yml',
        'wizard/hr_timesheet_wiz_view.xml',
        'wizard/hr_prime_type_wiz.xml',
        'wizard/confirmation_state_view.xml',
		# 'wizard/employee_wizard_views.xml',
        'data/ir_actions_act_windows.xml',
        'data/fields_export.xml',
        'data/mail_template_data.xml',
        'data/hr_contract_qualification_data.xml',
        'data/hr_contract_model_data.xml',
        'data/ir_sequence_data.xml',
        'data/outgoing_server_mail_data.xml',
        'data/hr_decimal_precision_data.xml',
        'security/ir.model.access.csv',


        # MENU
        'views/ir_ui_menu_root.xml',

        'views/hr_contract_view.xml',
        #'views/paie_state.xml',
#         'views/log_dirickx_db_view.xml',
#         'views/hr_timesheet_sheet_inherit_view.xml',
        'views/res_partner_bank_inherit_view.xml',
        'report/report_fiche_paie.xml',
        'report/report_STC.xml',
        'report/layout_footer_view.xml',
        'report/layout_header_view.xml',
        'views/drx_sequence.xml',
        'views/hr_employee_view.xml',
        'views/hr_enfant_view.xml',
        'views/res_company_view.xml',
        'views/hr_payslip_view.xml',
        'views/hr_contract_type_view.xml',
        'views/hr_attendance_view.xml',
        'views/hr_copefrito_paie_assets_view.xml',
#         'views/timesheet_cron_config_view.xml',
#         'views/hr_timesheet_workflow_inherit.xml',
        'views/ir_cron.xml',
        'views/copefrito_report_file_view.xml',
        'views/hr_payslip_payment_mode_view.xml',
        'views/hr_timesheet_sheet_wizard_view.xml',
        'views/hr_salary_rule.xml',
        'views/hr_holidays_view_inherit.xml',
        'views/hr_holidays_status_view_inherit.xml',
        'views/hr_contract_qualification_view.xml',
        'views/hr_payslip_run_view.xml',
        'views/hr_payslip_class_config.xml',
        'views/hr_payslip_rubric_config.xml',
        'views/hr_department.xml',
        'views/hr_payslip_rubric_view.xml',
        'views/hr_payslip_class_view.xml',
        'views/hr_job_view_inherit.xml',
        'views/point_indice_view.xml',
        'views/operator_card_view.xml',
        'views/webclient_templates.xml',
        'views/hr_contract_model.xml',
        'views/hr_payslip_input_vs_line_view.xml',
        'views/res_users_view.xml',
        'views/copefrito_config_views.xml',
        'views/hr_decimal_precision.xml',
        # 'views/hr_payslip_input_view.xml',
       
		

        # MENU
        'views/ir_ui_menu.xml',

        #SECURITY
        'security/hr_copefrito_paie_rule.xml',
    ],
    "qweb": [
        'static/src/xml/timesheet.xml',
        'static/src/xml/base_inherit.xml',
    ],
    "js": [
        'static/src/js/timesheet.js',
        'static/src/js/payslip_line_report.js',
        'static/src/js/form_widgets.js',
        'static/src/js/tree_widgets.js',
        'static/src/js/toggle_button_orange.js',
        'static/src/js/date_picker.js',
        'static/src/js/list_editor.js',
    ],
    'demo': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': [],
}