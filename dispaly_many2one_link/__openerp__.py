# -*- coding: utf-8 -*-

{
    'name': 'Display many2one',
    'summary': """
       Many2one's field display mode after click""",
    'version': '9.0.1.0.0',
    'description': 'When we click on many2one fields all buttons and actions in the form should disappear',
    'license': 'AGPL-3',
    'author': 'Etech',
    'website': 'https://www.etechconsulting-mg.com/',
    'depends': [
        'base',
    ],
    'sequence': 2,
    'installable': True,
    'data':[
        'views/display_m2o_asset_backend.xml'
    ]
}