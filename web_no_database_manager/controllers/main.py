import openerp
from openerp import http
from openerp.exceptions import AccessError
import jinja2
import os
import sys

from openerp.addons import web

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('openerp.addons.web_no_database_manager', "views")

env = jinja2.Environment(loader=loader, autoescape=True)

db_monodb = http.db_monodb

class Database(web.controllers.main.Database):

    def _render_template(self, **d):
        d.setdefault('manage',True)
        d['insecure'] = openerp.tools.config['admin_passwd'] == 'admin'
        d['list_db'] = openerp.tools.config['list_db']
        d['langs'] = openerp.service.db.exp_list_lang()
        d['countries'] = openerp.service.db.exp_list_countries()
        # databases list
        d['databases'] = []
        try:
            d['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            monodb = db_monodb()
            if monodb:
                d['databases'] = [monodb]
        return env.get_template("database_no_manager.html").render(d)