# -*- encoding: utf-8 -*-
{
    'name': 'Copefrito HR',
    'version': '1.0',
    'author': 'Etech Vahinisoa, Sylvain Michel R.',
    'website': 'www.etechconsulting-mg.com',
    'description': """
Some customizations for hr module.""",
    'depends': [
        'web',
        'hr_copefrito_paie',
    ],
    'data': [
        'views/copefrito_hr_assets_view.xml',
    ],
    "js": [
        'static/src/js/form_view.js',
    ],
    'installable': True,
}
