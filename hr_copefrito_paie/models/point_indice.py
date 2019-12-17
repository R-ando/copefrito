# -*- coding: utf-8 -*-
import time
from datetime import date
from datetime import datetime

from openerp import models, api, fields, tools
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from lxml import etree


class point_indice(models.Model):
    _name = 'point.indice'
    _sql_constraints = [
        ('point_indice_effective_date_uniq', 
         'UNIQUE (effective_date)', 
         'La date de prise d\'effet doit être unique')]
    
    name = fields.Char('Nom')
    company_id = fields.Many2one('res.company', string=u'Société', default = lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', string=u'Devise')
    effective_date = fields.Date(string=u'Date de prise d\'effet', required=True, default=lambda *a: time.strftime("%Y-%m-%d"))
    amount  = fields.Float('Valeur point d\' indice ', digits=(16, 4))
    reference_decree = fields.Text(u"Référence décret")
    application_date = fields.Date(string=u"Date d'application")
    
    @api.one
    @api.onchange('effective_date')
    def _onchange_effective_date(self):
        if self.effective_date:
            #date = datetime.fromtimestamp(time.mktime(time.strptime(self.effective_date, "%Y-%m-%d")))
            #self.name = ("Point d'indice du %s")%(tools.ustr(date.strftime('%d %B %Y')))
            self.name = ("Point d'indice du %s")%(self.convert_date_to_french_string(self.effective_date))
            
    @api.one
    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.currency_id = self.company_id.currency_id
        
    @api.model
    def convert_date_to_french_string(self, date):
        str_month = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
        format_date = datetime.strptime(str(date), "%Y-%m-%d")
        jour = format_date.day
        mois = format_date.month
        annee = format_date.year
        return str(jour)+" "+str_month[int(mois-1)]+" "+str(annee)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(point_indice, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        active_user = self.env.user
        if active_user.has_group('hr_copefrito_paie.group_direction'):
            if view_type == 'tree':
                for node in doc.xpath('//tree'):
                    node.set('create', 'false')
                    node.set('delete', 'false')
            elif view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        if not active_user.has_group('hr_copefrito_paie.group_pay_manager'):
            if view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        result['arch'] = etree.tostring(doc)
        return result