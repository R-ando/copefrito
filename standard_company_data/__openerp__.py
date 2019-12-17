# -*- coding: utf-8 -*-

{
    'name': 'Données Copefrito',
    'summary': """
       Data for Copefrito company""",
    'version': '9.0.1.0.0',
    'description': 'Data for standard company',
    'license': 'AGPL-3',
    'author': 'Etech',
    'website': 'https://www.etechconsulting-mg.com/',
    'depends': [
        'base', 'hr_copefrito_paie'
    ],
    'installable': True,
    'data':[
        'data/hr_payslip_config_data.xml',
    ]
}