# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.exceptions import UserError
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import logging

import random
import psycopg2
import datetime
import time
#from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

import sys
_logger = logging.getLogger(__name__)


class hr_timesheet_sheet(models.Model):    
    _inherit = "hr_timesheet_sheet.sheet"
    
    @api.multi
    @api.depends('employee_id')
    def _set_id_number(self):  ##-
        """
        Get id number according to contract of employee
        """
        for rec in self:
        	if str(rec.employee_id.identification_cdi_id) != '0' and rec.employee_id.identification_cdi_id != False: 
        		rec.id_number = str(rec.employee_id.identification_cdi_id)
        	else:
        		rec.id_number = str(rec.employee_id.identification_id)

    @api.multi
    @api.depends('employee_id')
    def _set_work_night_state(self):  ##-
        """
        Get work_night value according to employee
        """
        for rec in self:
        	rec.work_night_state = rec.employee_id.contract_id.work_night

    @api.multi
    @api.depends('employee_id')
    def _set_contract_hours_type(self):  ##-
        """
        Get work_night value according to employee contract type
        """
        print self.employee_id.contract_id
        for rec in self:
            rec.contract_hours_type = rec.employee_id.contract_id.monthly_hours_amount_id.hours

    @api.multi
    def _default_date_from(self):
        user = self.env['res.users'].browse(self._uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'
        if r=='month':
            return time.strftime('%Y-%m-20')
        elif r=='week':
            return (datetime.datetime.today() + relativedelta(weekday=0, days=-6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-01-01')  
        return fields.date.context_today()                  

    @api.multi
    def _default_date_to(self):
        user = self.env['res.users'].browse(self._uid)
        r = user.company_id and user.company_id.timesheet_range or 'month'        
        if r=='month':
            return (datetime.datetime.today() + relativedelta(months=+1,day=20,days=-1)).strftime('%Y-%m-%d')
        elif r=='week':
            return (datetime.datetime.today() + relativedelta(weekday=6)).strftime('%Y-%m-%d')
        elif r=='year':
            return time.strftime('%Y-12-31')
        return fields.date.context_today()
    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        context.update({'hide_all_update_total': False})        
        print "create hr_timesheet_sheet"
        #employee_obj = self.env['hr.employee']
        employee_obj = self.pool.get('hr.employee')
        user_obj = self.pool.get('res.users')

        new_user_id = self.pool.get('hr.employee').browse(cr, uid, vals['employee_id'], context=context).user_id.id or False
        if not new_user_id:
                employee = employee_obj.browse(cr, uid, vals['employee_id'], context=context)
                #print "-------> name : ",employee.name_related

                random_name = "".join(str(employee.name_related).lower().split())+str(random.randrange(1, 999999)) ##-
                data_user = {
                    'login': random_name,
                    'name': random_name,
                    'email': random_name+"@",
                }
                assignee_id = int(user_obj.create(cr, uid, data_user)) #create user

                data_employee = {
                    'user_id': assignee_id
                }        
                line_id = employee_obj.search(cr, uid, [('id','=',vals['employee_id'])])
                
                write = employee_obj.write(cr, uid,line_id, data_employee) #create employee
                print "Update Employee status : ",write

        return super(hr_timesheet_sheet, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        context.update({'hide_all_update_total': False})
        if vals.has_key('state') and vals['state'] == 'draft':
            vals['state'] = 'new'
        if vals.has_key('total_timesheet_for_pay'):
            vals['update_total_timesheet_for_pay'] = True
        if vals.has_key('total_hours_sup_for_pay'):
            vals['update_total_hours_sup_for_pay'] = True
        if vals.has_key('total_sundays_hours_for_pay'):
            vals['update_total_sundays_hours_for_pay'] = True
        if vals.has_key('total_holidays_hours_for_pay'):
            vals['update_total_holidays_hours_for_pay'] = True
        if vals.has_key('total_night_hours_for_pay'):
            vals['update_total_night_hours_for_pay'] = True                                                
        res = super(hr_timesheet_sheet, self).write(cr, uid, ids, vals, context=context)
        return res

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO CHANGE NAME OF TIMESHEETS IN PAYSLIP
    @Author: Sylvain Michel R.
    @Begins on : 12/01/2017
    @Latest update on : 12/01/2017
    __________________________________________________________________________________________

    """            

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        # week number according to ISO 8601 Calendar
        return [(r['id'], str(datetime.datetime.strptime(r['date_from'], '%Y-%m-%d').strftime('%m/%Y')) + ' - ' + self.browse(cr, uid, ids)[0].employee_id.name) \
                for r in self.read(cr, uid, ids, ['date_from'],
                    context=context, load='_classic_write')]                                           

    state = fields.Selection([
        ('new', u'Nouveau'),
        ('confirm', u'En Attente d\'approbation'),
        ('done', u'Confirmé'),
        ('cancel', u'Annulé'),], 'Status', select=True, required=True, readonly=True,
        track_visibility='onchange',
        help=u' * Le statut \'Confirmé\' est utilisé pour confirmer la feuille de temps par l\'utilisateur. \
            \n* Le statut \'Terminée\' est utilisé lorque les feuilles de temps sont acceptées par le/la responsable. \
            \n* Le statut \'Annulée\' est utilisé lorsque les feuilles de temps sont refusées par le/la responsable.')


    employee_id =  fields.Many2one('hr.employee', 'Employee', required=True)
    #identification_cdi_id = fields.Integer(u'Matricule', related='employee_id.identification_cdi_id',store=True, readonly=True)
    work_night_state  = fields.Boolean(u'Travail de nuit', compute='_set_work_night_state',readonly = True) ##-
    id_number = fields.Char(compute='_set_id_number',
                              string=u'Matricule',
                              help=u'Matricule selon le contract',
                              readonly=True,default =u'Matricule', store=True)
    contract_hours_type  = fields.Float(u'Heure contrat', compute='_set_contract_hours_type',readonly = True, store=True) ##-

    date_from = fields.Date('Date from', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}, default=_default_date_from)
    date_to = fields.Date('Date to', required=True, select=1, readonly=True, states={'new':[('readonly', False)]}, default=_default_date_to)

    total_timesheet_for_pay = fields.Float(u"Total des heures travaillées interprété")
    total_hours_sup_for_pay = fields.Float(u"Total des heures supplémentaires interprété")
    total_sundays_hours_for_pay = fields.Float(u"Total des heures sur dimanche interprété")
    total_holidays_hours_for_pay = fields.Float(u"Total des heures sur jours fériés interprété")
    total_night_hours_for_pay = fields.Float(u"Total des heures nuits interprété") 

    update_total_timesheet_for_pay = fields.Boolean(u"MAJ Total des heures travaillées interprété", default=False)
    update_total_hours_sup_for_pay = fields.Boolean(u"MAJ Total des heures supplémentaires interprété", default=False)
    update_total_sundays_hours_for_pay = fields.Boolean(u"MAJ Total des heures sur dimanche interprété", default=False)
    update_total_holidays_hours_for_pay = fields.Boolean(u"MAJ Total des heures sur jours fériés interprété", default=False)
    update_total_night_hours_for_pay = fields.Boolean(u"MAJ Total des heures nuits interprété", default=False)     

    total_timesheet = fields.Float(u"Total des heures travaillées", readonly = True, compute='_set_total_timesheet', store=True)
    total_hours_sup  = fields.Float(u"Total des heures supplémentaires", readonly = True, compute='_set_total_hours_sup', store=True)
    total_sundays_hours  = fields.Float(u"Total des heures sur dimanche", readonly = True, compute='_set_total_sundays_hours', store=True)
    total_holidays_hours  = fields.Float(u"Total des heures sur jours fériés", readonly = True, compute='set_total_holidays_hours', store=True)
    total_night_hours  = fields.Float(u"Total des heures nuits", readonly = True, compute='_set_total_night_hours', store=True)

    """
    __________________________________________________________________________________________

    @Description : FUNCTIONS TO HIDE FIELDS IN ADVANCED SEARCH 
    @Author: Sylvain Michel R.
    @Begins on : 13/01/2017
    @Latest update on : 25/01/2017
    __________________________________________________________________________________________

    """

    @api.model
    def fields_get(self, fields=None):
        fields_to_hide = ['update_total_timesheet_for_pay',
                        'update_total_hours_sup_for_pay',
                        'update_total_sundays_hours_for_pay',
                        'update_total_holidays_hours_for_pay',
                        'update_total_night_hours_for_pay'
                        ]
        # you can set this dynamically
        res = super(hr_timesheet_sheet, self).fields_get(fields)
        if not self._context.has_key('hide_all_update_total'):
            for field in fields_to_hide: 
                res[field]['selectable'] = False        
        return res

    """
    __________________________________________________________________________________________

    @Description : FUNCTIONS TO COMPUTE AUTOMATICALLY COMPUTED/INTERPRETED FIELDS
    @Author: Sylvain Michel R.
    @Begins on : 22/12/2016
    @Latest update on : 25/01/2017
    __________________________________________________________________________________________

    """     

    @api.one
    @api.depends('timesheet_ids')
    def _set_total_timesheet(self):
        """ Compute the attendances, analytic lines timesheets and differences between them
            for all the days of a timesheet and the current day
        """

        if self.id:
            self._cr.execute("""
                SELECT sum(total_timesheet) as total_timesheet
                FROM hr_timesheet_sheet_sheet_day
                WHERE sheet_id = %s
                GROUP BY sheet_id
            """, (self.id,))

            res = self._cr.dictfetchall()
            if res: self.total_timesheet = res[0]['total_timesheet']

    @api.one
    @api.depends('timesheet_ids')
    def _set_total_hours_sup(self):
        hc = self.employee_id.contract_id.monthly_hours_amount_id.hours
        ht = self.total_timesheet
        result = ht - hc
        if result > 0:
            self.total_hours_sup = result
        else:
            self.total_hours_sup = 0
        if self.id and self.timesheet_ids:
            try:
                if self.update_total_timesheet_for_pay is False:
                    self.total_timesheet_for_pay = self.total_timesheet
                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_timesheet_for_pay=%s WHERE id=%s """,(self.total_timesheet,self.id,))
                if self.employee_id.company_id.additional_hours_authorized:
                    if self.update_total_hours_sup_for_pay is False:
                        if result > 0:
                            if hc == 240:
                                if result < 84.0:
                                    self.total_hours_sup_for_pay = result
                                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(result,self.id,))
                                else:
                                    self.total_hours_sup_for_pay = 84.0
                                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(84.0,self.id,))
                            elif hc == 312:
                                if result < 12.0:
                                    self.total_hours_sup_for_pay = result
                                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(result,self.id,))
                                else:
                                    self.total_hours_sup_for_pay = 12.0
                                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(12.0,self.id,))
                        else:
                            self.total_hours_sup_for_pay = 0
                            self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(0.0,self.id,))
                else:
                    self.total_hours_sup_for_pay = 0.0
                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_hours_sup_for_pay=%s WHERE id=%s """,(0.0,self.id,))
            except:
                _logger.info("No updates")
                return False

    @api.one
    @api.depends('timesheet_ids')
    def _set_total_sundays_hours(self):
        result = 0
        result_for_pay = 0
        for timesheet_id in self.timesheet_ids:
            timesheet_date = datetime.datetime.strptime(str(timesheet_id.date), "%Y-%m-%d")
            dayoff = self.env['training.holiday.period'].search([('date_start','>=',timesheet_date),('date_stop','<=',timesheet_date)])
            
            if int(timesheet_date.strftime('%w')) in [0]:
                result += timesheet_id.unit_amount
                if timesheet_id.account_id.name == 'Travail de Nuit' and timesheet_id.unit_amount == 6:
                    result += 6
                if self.employee_id.company_id.additional_hours_authorized:
                    if not dayoff and (self.employee_id.company_id.hours_right) and self.employee_id.contract_id.monthly_hours_amount_id.hours != 312:
                        result_for_pay += timesheet_id.unit_amount
                        if timesheet_id.account_id.name == 'Travail de Nuit' and timesheet_id.unit_amount == 6:
                            result_for_pay += 6
            
        self.total_sundays_hours = result
        
        if self.id:
            if self.update_total_sundays_hours_for_pay is False:
                self.total_sundays_hours_for_pay = result_for_pay
                self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_sundays_hours_for_pay=%s WHERE id=%s """,(result_for_pay,self.id,))    
            self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_sundays_hours=%s WHERE id=%s """,(result,self.id))      

    @api.one
    @api.depends('timesheet_ids')
    def set_total_holidays_hours(self):
        result = 0.0
        result_for_pay = 0.0
        for timesheet_id in self.timesheet_ids:
            
            timesheet_date = datetime.datetime.strptime(str(timesheet_id.date), "%Y-%m-%d")        
            dayoff = self.env['training.holiday.period'].search([('date_start','>=',timesheet_date),('date_stop','<=',timesheet_date)])  
            
            if dayoff:
                result += timesheet_id.unit_amount
                if timesheet_id.account_id.name == 'Travail de Nuit' and timesheet_id.unit_amount == 6:
                    result += 6
        
        if self.employee_id.company_id.additional_hours_authorized:
            result_for_pay = result
            
        self.total_holidays_hours = result
        if self.id:
            if self.update_total_holidays_hours_for_pay is False:
                if self.employee_id.company_id.hours_right:
                    self.total_holidays_hours_for_pay = result_for_pay
                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_holidays_hours_for_pay=%s WHERE id=%s """,(result_for_pay,self.id,))
                else:
                    self.total_holidays_hours_for_pay = 0.0
                    self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_holidays_hours_for_pay=%s WHERE id=%s """,(0.0,self.id,))
            self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_holidays_hours=%s WHERE id=%s """,(result,self.id))

    @api.one
    @api.depends('timesheet_ids')
    def _set_total_night_hours(self):
        result = 0
        result_for_pay = 0
        for timesheet_id in self.timesheet_ids:
            if timesheet_id.account_id.name == 'Travail de Nuit':
                timesheet_date = datetime.datetime.strptime(str(timesheet_id.date), "%Y-%m-%d")        
                dayoff = self.env['training.holiday.period'].search([('date_start','>=',timesheet_date),('date_stop','<=',timesheet_date)])   
                result += timesheet_id.unit_amount
                if self.employee_id.company_id.additional_hours_authorized:
                    if self.employee_id.company_id.hours_right:
                        if self.employee_id.contract_id.monthly_hours_amount_id.hours != 312:
                            result_for_pay += timesheet_id.unit_amount
                            if dayoff or int(timesheet_date.strftime('%w')) in [0]:
                                if timesheet_id.unit_amount == 6 or timesheet_id.unit_amount == 12:
                                    result_for_pay -= 12
        self.total_night_hours = result
        if self.id:
            if self.update_total_night_hours_for_pay is False:
                result_night_for_pay = (result_for_pay/12)*7
                self.total_night_hours_for_pay = result_night_for_pay
                self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_night_hours_for_pay=%s WHERE id=%s """,(result_night_for_pay,self.id,))        
            self._cr.execute(""" UPDATE hr_timesheet_sheet_sheet SET total_night_hours=%s WHERE id=%s """,(result,self.id))

        
    """
    __________________________________________________________________________________________

    @Description : CLASS FOR ALL LOGS WHICH WILL BE STORED IN DB : INFOS AND ERRORS
    @Author: Lanto
    @Begins on : 28/12/2016
    __________________________________________________________________________________________

    """

    class log_dirickx_db(models.Model):    
        _name = "log.dirickx.db"
        _description = "Dirickx Log Table"

        date_log = fields.Datetime(u'Date du Log',readonly= True)           
        log_content = fields.Text(u'Log',readonly= True)           
        type_log =   fields.Char(u'Type de Log',readonly= True)            
        
        _order = 'date_log ASC'
                             
        ##-
        other_log = fields.Text(u'Autre donnée pour Log') #information if needed in some log creation
        
        
    class type_log_cron(models.Model):    
        _name = "type.log.cron"
        _description = "Dirickx Type Log Table"

        name = fields.Char(u'Type du log')           

    """
    __________________________________________________________________________________________

    @Description : CLASS FOR THE CRON IMPORTING ALL DATA FROM MOBILE DB SYSTEM TO ODOO
    @Author: Lanto RAZAFINDRABE
    @Begins on : 21/12/2016
    __________________________________________________________________________________________

    """
    class dirickx_remote_db(models.Model):    
        _name = "dirickx.remote.db"
        _description = "Dirickx Mobile Part"    

        host_db = fields.Char(u'Hôte',required = True)
        port_db = fields.Integer(u'Port',required = True)
        dbname = fields.Char(u'Nom de la base de données',required = True)
        password_db = fields.Char(u'Mot de passe')
        user_db = fields.Char(u'Utilisateur',required = True)


        cron_title = fields.Char(u'Cron de lancement',readonly = True)
        cron_state = fields.Boolean(u'En cours',readonly = True)
        date_run = fields.Date(u'Date de rapatriement')
        only_one = fields.Integer(u'N°',default = 1,readonly = True)
        
        
        _sql_constraints = [
            ('only_one_unique', 'unique(only_one)', u'Seulement une configuration permise!')
        ]


        def connect(self):
            """
            @Description: Here we must specify on cron configuration all parameters for connecting to Mobile DB side
            
            """
            cron_timesheet_obj = self.pool.get('dirickx.remote.db')
            cr = self.env.cr; uid= self.env.uid
            id_cron = cron_timesheet_obj.search(cr, uid, [('only_one','=','1')])
            if id_cron:
                    for cron_line in cron_timesheet_obj.browse(cr,uid,id_cron):
                        if cron_line:
                            host_db = cron_line.host_db
                            port_db = cron_line.port_db
                            dbname = cron_line.dbname
                            user_db = cron_line.user_db
                            password_db = cron_line.password_db
                            if password_db == None or password_db == False:
                                password_db = ''
                        else:
                            _logger.error(u"Pas de configuration de la base pour le CRON.")
                            if id_cron:
                                cr.execute("update dirickx_remote_db set cron_state = False")
                                cr.commit()
                            return False
            else:
                _logger.error(u"Pas de configuration de la base pour le CRON.")
                return False
            if host_db.strip() == 'localhost':
                conn_string = "host='%s' dbname='%s' user='%s' password='%s'"%(host_db,dbname,user_db,password_db)            
            else:
                conn_string = "host='%s' port='%s' dbname='%s' user='%s' password='%s'"%(host_db,port_db,dbname,user_db,password_db)            

            print "Connecting to database\n ->%s" % (conn_string)

            try:
                conn = psycopg2.connect(conn_string)
                self.conn = conn
                print "Connection Object: %s" % (self.conn)                
            except Exception as e:
                _logger.error(u'Connection to the database failed')
                return False


        def isNumber(self,Chaine):
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
            i=0
            sCh  = str(Chaine)
            while(i<len(sCh)):
                if(sCh[i] in chiffre):
                    res = True
                else:
                    return False
                i=i+1
            return res


        @api.model
        def retrieve_data(self):
            """
            The base of the CRON
            """

            self.connect()
            try:

                print "--- Retrieving Data  ---"

                cursor = self.conn.cursor()
                cr = self.env.cr; uid= self.env.uid

                analytic_line_obj = self.pool.get('account.analytic.line')
                analytic_account_obj = self.pool.get('account.analytic.account')
                employee_obj = self.pool.get('hr.employee')
                hr_timesheet_sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
                cron_timesheet_obj = self.pool.get('dirickx.remote.db')
                
                
                # update status of cron : en cours > True
                id_cron = cron_timesheet_obj.search(cr, uid, [('only_one','=','1')])
                
                def send_log(log_content = None,type_log='ERROR'):
                    log_cron_obj = self.pool.get('log.dirickx.db')
                    log_data = {
                        'log_content':log_content,
                        'type_log': type_log,
                        'date_log':str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]),
                        }                                    
                    log_cron_obj.create(cr, uid, log_data)

                def stop_and_change_status():
                    id_cron = cron_timesheet_obj.search(cr, uid, [('only_one','=','1')])
                    # update status of cron : en cours > False
                    if len(id_cron)>0:  
                        cr.execute("update dirickx_remote_db set cron_state = False")
                        cr.commit()
                    return False

                #_logger.info(u">>>>>>> CRON STATUS: %s"%id_cron)

                if len(id_cron)>0:                    
                    #print cron_timesheet_obj.browse(cr,uid,id_cron[0])
                    for cron_line in cron_timesheet_obj.browse(cr,uid,id_cron[0]):                        
                        if cron_line:
                            print "Date of sync : ",cron_line.date_run                            
                            if cron_line.date_run !='' and cron_line.date_run:
                                # if the date in config is at the future no today or a date in the past, so we did error
                                if datetime.datetime.strptime(cron_line.date_run, '%Y-%m-%d') > datetime.datetime.strptime(datetime.date.today().strftime('%Y-%m-%d'), '%Y-%m-%d'):
                                    _logger.error(u"Erreur sur la valeur de la date de rapatriement dans la configuration du CRON.\n Date en avance! à effacer ou à bien régler.")                                                                        
                                    send_log(u"""Erreur sur la valeur de la date de rapatriement dans la configuration du CRON.
                                                \n Date en avance! à effacer ou à bien régler. 
                                                \n Renseigné au configuration cron: %s"""%str(cron_line.date_run))
                                    stop_and_change_status()
                                else:
                                    #SELECT ALL from the date_run to today
                                    sql = """
                                        (select id, debut_controle, fk_controlleur,fk_site,token from bodir_controle 
                                        where debut_controle >= '%s' and debut_controle <= TIMESTAMP 'today')

                                        UNION 
                                        (SELECT id, debut_controle, fk_controlleur,fk_site,token 
                                                    FROM bodir_controle
                                                    WHERE last_updated is not NULL);  """%cron_line.date_run                                    
                            else:
                                #SELECT ALL WITH YESTERDAY of cURRENT Date                                 
                                sql = """
                                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                                    FROM bodir_controle
                                                    WHERE debut_controle >= TIMESTAMP 'yesterday') 

                                                    EXCEPT 
                                                    
                                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                                    FROM bodir_controle
                                                    WHERE debut_controle >= TIMESTAMP 'today')
                                                    
                                                    UNION

                                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                                    FROM bodir_controle
                                                    WHERE last_updated is not NULL);

                                                    """

                        else:                    
                            #SELECT ALL WITH YESTERDAY of cURRENT Date                             
                            sql = """
                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                    FROM bodir_controle
                                    WHERE debut_controle >= TIMESTAMP 'yesterday') 

                                    EXCEPT 
                                    
                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                    FROM bodir_controle
                                    WHERE debut_controle >= TIMESTAMP 'today')
                                    
                                    UNION

                                    (SELECT id, debut_controle, fk_controlleur,fk_site,token
                                    FROM bodir_controle
                                    WHERE last_updated is not NULL);

                                    """
                #_logger.info(u">>>>>>> sql: %s"%sql)

                try:
                    cursor.execute(sql)
                    yesterday_lines = cursor.fetchall()
                    print yesterday_lines
                except:
                    _logger.error(u"Erreur rapatriement de données sur 'bodir_controle'.")
                    send_log(u"""Erreur rapatriement de données sur 'bodir_controle'. 
                                    \nFetchall avec la requête : %s"""%(sql))
                    stop_and_change_status()

                if yesterday_lines and len(yesterday_lines)>0:
                    for yesterday_line in yesterday_lines:
                        if yesterday_line:
                            print "\n>>>>> YESTERDAY <<<<<"
                            id_controle, debut_controle, fk_controlleur,fk_site,token= yesterday_line
                            
                            print id_controle
                            print debut_controle
                            print fk_controlleur
                            print fk_site
                            print token
                            """
                            -----------------------------------------------------------------------------
                            ---------------   SELECT EACH LOGIN OF AGENT BY CONTROLLER   ----------------
                            -----------------------------------------------------------------------------

                            """
                            # now trying to get matricule of employee based on fk_agent mobile part field
                            cursor.execute("""select 
                                                id,
                                                EXTRACT(HOUR FROM retard) as retard_hour,
                                                EXTRACT(MINUTE FROM retard) as retard_minute,
                                                EXTRACT(HOUR FROM prise_service) as prise_service_hour,
                                                EXTRACT(MINUTE FROM prise_service) as prise_service_minute,
                                                fk_agent,
                                                fk_controle 

                                                from bodir_controle_agent 

                                                where fk_controle =%s"""%id_controle)
                            try:
                                lines = cursor.fetchall()
                            except:
                                _logger.error(u"Erreur rapatriement de données sur 'bodir_controle_agent'.")             
                                send_log(u"""Erreur rapatriement de données sur 'bodir_controle_agent'.
                                                \nFetchall sur select id,EXTRACT(HOUR FROM prise_service) as prise_service_hour,EXTRACT(MINUTE FROM prise_service) as prise_service_minute,fk_agent,fk_controle from bodir_controle_agent 
                                                where fk_controle =%s"""%id_controle)             
                                stop_and_change_status()
                            if lines:
                                for line in lines:
                                    if line:
                                        id_controle_agent,retard_hour,retard_minute,prise_service_hour,prise_service_minute,fk_agent,fk_controle = line
                                        if retard_minute =="" or not retard_minute:
                                            retard_minute = 0
                                        if retard_hour =="" or not retard_hour:
                                            retard_hour = 0
                                        cursor.execute("select id,matricule,etat from bodir_employe where id =%s"%fk_agent)
                                        try:
                                            employees = cursor.fetchall()
                                        except:
                                            _logger.error(u"Erreur rapatriement de données sur 'bodir_employe'.")
                                            send_log(u"""Erreur rapatriement de données sur 'bodir_employe'.
                                                            \nFetchall sur select id,matricule from bodir_employe where id =%s"""%fk_agent)
                                            stop_and_change_status()
                                        if employees:
                                            for employe in employees:
                                                if employe:
                                                    id_employe,matricule,etat_active_employe = employe

                                                    if self.isNumber(matricule):
                                                        line_id = employee_obj.search(cr, uid, [('identification_cdi_id','=',str(matricule).strip().replace(" ",""))])
                                                        if not line_id:
                                                            line_id = employee_obj.search(cr, uid, [('identification_id','=',str(matricule).strip().replace(" ",""))])
                                                    else:
                                                        line_id = employee_obj.search(cr, uid, [('identification_id','=',str(matricule).strip().replace(" ",""))])
                                                    if line_id and len(line_id)<2:
                                                        for line in employee_obj.browse(cr, uid, line_id):                                                                                                        
                                                            if line:
                                                                try:
                                                                    print "User id :%s"% line.user_id.id
                                                                    user_id = line.user_id.id #ok for query analytic account line
                                                                except:
                                                                    _logger.error(u"Cas liaison matricule Mobile et matricule Odoo: Détection de l'user_id de l'employé associé au matricule échouée.")
                                                                    send_log(u"""Cas liaison matricule Mobile et matricule Odoo: Détection de l'user_id de l'employé associé au matricule échouée.
                                                                                    \nline_id: %s sur employee_obj"""%line_id)
                                                                    stop_and_change_status()
                                                            else:
                                                                _logger.error(u"La matricule %s n'est pas associé à aucun utilisateur."%matricule)
                                                                send_log(u"La matricule %s n'est pas associé à aucun utilisateur."%matricule)
                                                                stop_and_change_status()
                                                                    
                                                    else:
                                                        _logger.info(u"ATTENTION : LA MATRICULE %s A ETE UTILISE PLUS D'UNE FOIS. Ou n'existe pas dans la base 'hr.employee'.\nVérifiez l'utilisateur relié à l'employé s'il y en a."%matricule)
                                                        send_log(u"ATTENTION : LA MATRICULE %s A ETE UTILISE PLUS D'UNE FOIS. Ou n'existe pas dans la base 'hr.employee'.\nVérifiez l'utilisateur relié à l'employé s'il y en a."%matricule,"INFO")
                                                        user_id = False
                                                        #stop_and_change_status()
                                        else:
                                            send_log(u"ATTENTION : la clé fkagent dans bodir_controle_agent n'est pas reliée à aucun id dans bodir_employe","INFO")
                                            user_id = False



                                        # the rules about "travail de jour" and "travail de nuit" depends on the hour of the control not "prise_service"
                                        controle_hour = debut_controle.split(' ')[1]
                                        controle_hour = float(controle_hour[0:2]+'.'+controle_hour[3:5])


                                        """
                                        -----------------------------------------------------------------------------
                                        ---------------------------  IF PRISE DE SERVICE JOUR  ----------------------
                                        -----------------------------------------------------------------------------

                                        """
                                        if controle_hour>=6 and  controle_hour<=18: #no tolerances, exactly
                                            account_line = analytic_account_obj.search(cr, uid, [('name','=','Travail de Jour')])
                                            print "account_line jour : ",account_line
                                            if account_line:
                                                for account in analytic_account_obj.browse(cr, uid, account_line):
                                                    if account:
                                                        account_id = account.id #ok for query analytic account line
                                                        print "Le compte analytique JOUR avec id : %s est: %s"%(account.id, account.name)
                                                        date_presence = debut_controle.split(' ')[0] 
                                                        print 'date_presence: ',date_presence

                                                        """
                                                        part for unit_amount

                                                        """
                                                        #retard_float = round(float(retard_hour+(float(retard_minute)/60)))
                                                        unit_amount = 12 #- retard_float #ok for query analytic account line
                                                        print "print user_id JOUR : ",user_id

                                                        if user_id :   
                                                            ready_for_create = True

                                                            analytic_account_line_data = {
                                                                    'date': date_presence,
                                                                    'user_id': user_id,
                                                                    'account_id': account_id,
                                                                    'unit_amount': unit_amount,
                                                                    'name':'',      # TO CHANGE: data default Dirickx Time at Day
                                                                    'is_timesheet':True,
                                                                    'bodir_controle_id':id_controle,
                                                                    'bodir_controle_agent_id':id_controle_agent,
                                                                }
                                                            
                                                            # THEN, IF THE SHEET FOR THE USER_ID and THE DATE already exist: don't recreate line
                                                            print "print id controle + agent"
                                                            print id_controle
                                                            print id_controle_agent
                                                            print "before search"
                                                            
                                                            #_____________________________________________________________________________________|
                                                            #test sql if there is already a timesheet related to the user_id of the employee
                                                            #and the date of the timesheet is between 20 and 19, AND the date_presence is between this date
                                                            #if TRUE: test if this timesheet is not in state "done"

                                                            try:
                                                                cr.execute("""
                                                                    select id, state 
                                                                        from hr_timesheet_sheet_sheet 
                                                                    where 
                                                                        user_id = %s 
                                                                        and 
                                                                        date_to >= '%s'
                                                                        and 
                                                                        date_from <= '%s';"""%(user_id,date_presence,date_presence))
                                                                hr_timesheet_sheet_dt = cr.fetchall()
                                                            except:
                                                                _logger.error('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                send_log('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                pass

                                                            #if the employe is deactivated (non-active)
                                                            if str(etat_active_employe) == '0':
                                                                ready_for_create = False

                                                            #the timesheet is already confirmed
                                                            if hr_timesheet_sheet_dt and len(hr_timesheet_sheet_dt)>0 :
                                                                for timesheet_line in hr_timesheet_sheet_dt:
                                                                    if timesheet_line:
                                                                        timesheet_id, timesheet_state = timesheet_line
                                                                        if timesheet_state == 'done':
                                                                            ready_for_create = False
                                                                            break
                                                            #_____________________________________________________________________________________| 

                                                            id_bodir_controle = analytic_line_obj.search(cr, uid, ['&',('bodir_controle_id','=',id_controle),('bodir_controle_agent_id','=',id_controle_agent)])
                                                            print "---------------------------> id_bodir_controle: ",id_bodir_controle
                                                            if not id_bodir_controle:
                                                                try:
                                                                    if ready_for_create:
                                                                        creating = analytic_line_obj.create(cr, uid, analytic_account_line_data)
                                                                        print "----> JOUR create status analytic account: %s"%(creating)
                                                                    else:
                                                                        send_log('Date présence:%s ,ID utilisateur:%s ne peut pas être ajouté car feuille de temps déjà confirmé'%(date_presence,user_id),'INFO')
                                                                except:
                                                                    _logger.error('La création de la ligne de présence dans la partie JOUR rencontre un problème.')
                                                                    send_log('La création de la ligne de présence dans la partie JOUR rencontre un problème.')
                                                                    stop_and_change_status()                                                            
                                                            else:
                                                                #line already exist so UPDATE line
                                                                """try:
                                                                    if ready_for_create:
                                                                        updating = analytic_line_obj.write(cr, uid,id_bodir_controle, analytic_account_line_data)
                                                                        print "----> JOUR update status analytic account: %s"%(updating)

                                                                except:
                                                                    _logger.error('La mise à jour de la ligne de présence id %s dans la partie JOUR rencontre un problème.'%id_bodir_controle)
                                                                    send_log('La mise à jour de la ligne de présence id %s dans la partie JOUR rencontre un problème.'%id_bodir_controle)
                                                                    stop_and_change_status()"""

                                                                _logger.info(u"La ligne de controle JOUR %s existe déjà dans 'account_analytic_line'."%id_bodir_controle)
                                                                send_log(u"La ligne de controle JOUR %s existe déjà dans 'account_analytic_line'."%id_bodir_controle,"INFO")

                                                        #test_sheet_id = analytic_line_obj.browse(cr, uid, creating).sheet_id
                                                        #print "TEST SHEET ID: ", test_sheet_id                                                    

                                            else:
                                                _logger.info(u"Pas de type de présence trouvé pour le type jour. Doit être: 'Travail de Jour'.")
                                                send_log(u"Pas de type de présence trouvé pour le type jour. Doit être: 'Travail de Jour'.","INFO")


                                            """
                                                -----------------------------------------------------------------------------
                                                --------------------------- IF PRISE DE SERVICE NUIT  -----------------------
                                                -----------------------------------------------------------------------------
                                            """
                                        else: #work at night; From after 6pm to before 6am
                                            account_line = analytic_account_obj.search(cr, uid, [('name','=','Travail de Nuit')])
                                            print "account_line nuit: ",account_line
                                            if account_line:
                                                for account in analytic_account_obj.browse(cr, uid, account_line):
                                                    if account:
                                                        ready_for_create_1 = True
                                                        ready_for_create_2 = True

                                                        account_id = account.id #ok for query analytic account line
                                                        print "Le compte analytique NUIT avec id :%s est: %s"%(account.id, account.name)
                                                        
                                                        # THE NIGHT PART COMPOSE TWO RULES
                                                        controle_hour = debut_controle.split(' ')[1]
                                                        controle_hour = float(controle_hour[0:2]+'.'+controle_hour[3:5])

                                                        print "Night hours: ",controle_hour

                                                        
                                                        """
                                                        |------------------------------  FIRST RULE  --------------------------------|
                                                        
                                                        @Description: if control  hours between 6pm to midnight
                                                                        part of unit_amount from SFD, divided in two parts
                                                                        today date and tomorrow date
                                                        |-----------------------------------------------------------------------------|
                                                        """
                                                        if controle_hour >= 18 and controle_hour <= 23.59:
                                                            date_presence_part_1 = debut_controle.split(' ')[0] #ok for query analytic account line
                                                            print "Part 1 of Date de presence 1st rule: %s"%date_presence_part_1
                                                            
                                                            #get the next date from current date
                                                            current_date = (datetime.datetime.strptime(date_presence_part_1, '%Y-%m-%d') + datetime.timedelta(days=1))
                                                            next_date = current_date.strftime('%Y-%m-%d')
                                                            
                                                            date_presence_part_2 = next_date #ok for query analytic account line
                                                            
                                                            #retard_float = round(float(retard_hour+(float(retard_minute)/60)))
                                                            unit_amount_part_1 = 6 #- retard_float #ok for query analytic account line
                                                            unit_amount_part_2 = 6 #ok for query analytic account line
                                                            print "print user_id NUIT 1st RULE: ",user_id
                                                            if user_id : 
                                                                analytic_account_line_data_1 = {
                                                                    'date': date_presence_part_1,
                                                                    'user_id': user_id,
                                                                    'account_id': account_id,
                                                                    'unit_amount': unit_amount_part_1,
                                                                    'name':'',      # TO CHANGE: data default : Dirickx Time 1 - Rule 1
                                                                    'is_timesheet':True,
                                                                    'bodir_controle_id':id_controle,
                                                                    'bodir_controle_agent_id':id_controle_agent,                                                                     
                                                                }

                                                                analytic_account_line_data_2 = {
                                                                    'date': date_presence_part_2,
                                                                    'user_id': user_id,
                                                                    'account_id': account_id,
                                                                    'unit_amount': unit_amount_part_2,                                                        
                                                                    'name':'',    # TO CHANGE: data default  Dirickx Time 2 - Rule 1
                                                                    'is_timesheet':True,
                                                                    'bodir_controle_id':id_controle,
                                                                    'bodir_controle_agent_id':id_controle_agent,             
                                                                }

                                                                #_____________________________________________________________________________________|
                                                                #test sql if there is already a timesheet related to the user_id of the employee
                                                                #and the date of the timesheet is between 20 and 19, AND the date_presence is between this date
                                                                #if TRUE: test if this timesheet is not in state "done"
                                                                #------------------------------ FOR DATE PART 1 ---------------------|
                                                                try:
                                                                    cr.execute("""
                                                                        select id, state 
                                                                            from hr_timesheet_sheet_sheet 
                                                                        where 
                                                                            user_id = %s 
                                                                            and 
                                                                            date_to >= '%s'
                                                                            and 
                                                                            date_from <= '%s';"""%(user_id,date_presence_part_1,date_presence_part_1))
                                                                    hr_timesheet_sheet_dt = cr.fetchall()
                                                                except:
                                                                    _logger.error('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    send_log('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    pass

                                                                #if the employe is deactivated (non-active)
                                                                if str(etat_active_employe) == '0':
                                                                    ready_for_create = False

                                                                #the timesheet is already confirmed
                                                                if hr_timesheet_sheet_dt and len(hr_timesheet_sheet_dt)>0 :
                                                                    for timesheet_line in hr_timesheet_sheet_dt:
                                                                        if timesheet_line:
                                                                            timesheet_id, timesheet_state = timesheet_line
                                                                            if timesheet_state == 'done':
                                                                                ready_for_create_1 = False
                                                                                break
                                                                #------------------------------ FOR DATE PART 2 ---------------------|
                                                                try:
                                                                    cr.execute("""
                                                                        select id, state 
                                                                            from hr_timesheet_sheet_sheet 
                                                                        where 
                                                                            user_id = %s 
                                                                            and 
                                                                            date_to >= '%s'
                                                                            and 
                                                                            date_from <= '%s';"""%(user_id,date_presence_part_2,date_presence_part_2))
                                                                    hr_timesheet_sheet_dt = cr.fetchall()
                                                                except:
                                                                    _logger.error('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    send_log('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    pass

                                                                #if the employe is deactivated (non-active)
                                                                if str(etat_active_employe) == '0':
                                                                    ready_for_create = False

                                                                #the timesheet is already confirmed
                                                                if hr_timesheet_sheet_dt and len(hr_timesheet_sheet_dt)>0 :
                                                                    for timesheet_line in hr_timesheet_sheet_dt:
                                                                        if timesheet_line:
                                                                            timesheet_id, timesheet_state = timesheet_line
                                                                            if timesheet_state == 'done':
                                                                                ready_for_create_2 = False
                                                                                break                                                                
                                                                #_____________________________________________________________________________________|


                                                                
                                                                # THEN, IF THE SHEET FOR THE USER_ID and THE DATE already exist: don't recreate line
                                                                id_bodir_controle = analytic_line_obj.search(cr, uid, ['&',('bodir_controle_id','=',id_controle),('bodir_controle_agent_id','=',id_controle_agent)])
                                                                if not id_bodir_controle:
                                                                    try:
                                                                        if ready_for_create_1:
                                                                            creating_1 = analytic_line_obj.create(cr, uid, analytic_account_line_data_1)
                                                                            print "----> 1st RULE create status analytic account: %s "%(creating_1)
                                                                        else:
                                                                            send_log('Règle 1, Date présence partie 1 :%s ,ID utilisateur:%s ne peut pas être ajouté car feuille de temps déjà confirmé'%(date_presence_part_1,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('creating_1 dans RULE 1 rencontre un problème.')
                                                                        send_log('creating_1 dans RULE 1 rencontre un problème.')
                                                                        stop_and_change_status()


                                                                    try:
                                                                        if ready_for_create_2:
                                                                            creating_2 = analytic_line_obj.create(cr, uid, analytic_account_line_data_2)
                                                                            print "----> 1st RULE create status analytic account: %s"%(creating_2)
                                                                        else:
                                                                            send_log('Règle 1, Date présence partie 2 :%s ,ID utilisateur:%s ne peut pas être ajouté car feuille de temps déjà confirmé'%(date_presence_part_2,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('creating_2 dans RULE 1 rencontre un problème.')
                                                                        send_log('creating_2 dans RULE 1 rencontre un problème.')
                                                                        stop_and_change_status()
                                                                    
                                                                else:
                                                                    #line already exist so UPDATE line
                                                                    """
                                                                    try:
                                                                        if ready_for_create_1:
                                                                            updating_1 = analytic_line_obj.write(cr, uid,id_bodir_controle, analytic_account_line_data_1)
                                                                            print "----> 1st RULE update status analytic account: %s "%(updating_1)
                                                                        else:
                                                                            send_log('Règle 1, Date présence partie 1 :%s ,ID utilisateur:%s ne peut pas être mis à jour car feuille de temps déjà confirmé'%(date_presence_part_1,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('updating_1 dans RULE 1 rencontre un problème.')
                                                                        send_log('updating_1 dans RULE 1 rencontre un problème.')
                                                                        stop_and_change_status()


                                                                    try:
                                                                        if ready_for_create_2:
                                                                            updating_2 = analytic_line_obj.write(cr, uid,id_bodir_controle, analytic_account_line_data_2)
                                                                            print "----> 1st RULE update status analytic account: %s"%(updating_2)
                                                                        else:
                                                                            send_log('Règle 1, Date présence partie 2 :%s ,ID utilisateur:%s ne peut pas être  mis à jour car feuille de temps déjà confirmé'%(date_presence_part_2,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('updating_2 dans RULE 1 rencontre un problème.')
                                                                        send_log('updating_2 dans RULE 1 rencontre un problème.')
                                                                        stop_and_change_status()

                                                                    """
                                                                    _logger.info(u"La ligne de controle RULE 1, %s existe déjà dans 'account_analytic_line'."%id_bodir_controle)                                                                
                                                                    send_log(u"La ligne de controle RULE 1, %s existe déjà dans 'account_analytic_line'."%id_bodir_controle,"INFO")


                                                            """
                                                            |------------------------------  SECOND RULE  --------------------------------|
                                                            
                                                            @Description: if control  hours between midnight to 6am
                                                                            part of unit_amount from SFD, divided in two parts
                                                                            today date and yesterday date
                                                            |-----------------------------------------------------------------------------|
                                                            """                                                
                                                        elif controle_hour >= 0 and controle_hour <= 6 :
                                                            date_presence_part_1 = debut_controle.split(' ')[0]
                                                            print "Part 1 of Date de presence 2nd rule: %s"%date_presence_part_1 
                                                            
                                                            #get the next date from current date
                                                            current_date = (datetime.datetime.strptime(date_presence_part_1, '%Y-%m-%d') - datetime.timedelta(days=1))
                                                            next_date = current_date.strftime('%Y-%m-%d')
                                                            date_presence_part_2 = next_date

                                                            #retard_float = round(float(retard_hour+(float(retard_minute)/60)))
                                                            unit_amount_part_1 = 6 #ok for query analytic account line
                                                            unit_amount_part_2 = 6 #- retard_float
                                                            print "print user_id NUIT 2ND RULE: ",user_id
                                                            if user_id : 
                                                                analytic_account_line_data_1 = {
                                                                    'date': date_presence_part_1,
                                                                    'user_id': user_id,
                                                                    'account_id': account_id,
                                                                    'unit_amount': unit_amount_part_1,
                                                                    'name':'',    # TO CHANGE: data default Dirickx Time 1 - Rule 2
                                                                    'is_timesheet':True,
                                                                    'bodir_controle_id':id_controle,
                                                                    'bodir_controle_agent_id':id_controle_agent,                                                  
                                                                }

                                                                analytic_account_line_data_2 = {
                                                                    'date': date_presence_part_2,
                                                                    'user_id': user_id,
                                                                    'account_id': account_id,
                                                                    'unit_amount': unit_amount_part_2,                                                       
                                                                    'name':'',   # TO CHANGE: data default Dirickx Time 2 - Rule 2
                                                                    'is_timesheet':True,
                                                                    'bodir_controle_id':id_controle,
                                                                    'bodir_controle_agent_id':id_controle_agent,
                                                                }

                                                                #_____________________________________________________________________________________|
                                                                #test sql if there is already a timesheet related to the user_id of the employee
                                                                #and the date of the timesheet is between 20 and 19, AND the date_presence is between this date
                                                                #if TRUE: test if this timesheet is not in state "done"
                                                                #------------------------------ FOR DATE PART 1 ---------------------|
                                                                try:
                                                                    cr.execute("""
                                                                        select id, state 
                                                                            from hr_timesheet_sheet_sheet 
                                                                        where 
                                                                            user_id = %s 
                                                                            and 
                                                                            date_to >= '%s'
                                                                            and 
                                                                            date_from <= '%s';"""%(user_id,date_presence_part_1,date_presence_part_1))
                                                                    hr_timesheet_sheet_dt = cr.fetchall()
                                                                except:
                                                                    _logger.error('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    send_log('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    pass

                                                                #if the employe is deactivated (non-active)
                                                                if str(etat_active_employe) == '0':
                                                                    ready_for_create = False

                                                                #the timesheet is already confirmed
                                                                if hr_timesheet_sheet_dt and len(hr_timesheet_sheet_dt)>0 :
                                                                    for timesheet_line in hr_timesheet_sheet_dt:
                                                                        if timesheet_line:
                                                                            timesheet_id, timesheet_state = timesheet_line
                                                                            if timesheet_state == 'done':
                                                                                ready_for_create_1 = False
                                                                                break
                                                                #------------------------------ FOR DATE PART 2 ---------------------|
                                                                try:
                                                                    cr.execute("""
                                                                        select id, state 
                                                                            from hr_timesheet_sheet_sheet 
                                                                        where 
                                                                            user_id = %s 
                                                                            and 
                                                                            date_to >= '%s'
                                                                            and 
                                                                            date_from <= '%s';"""%(user_id,date_presence_part_2,date_presence_part_2))
                                                                    hr_timesheet_sheet_dt = cr.fetchall()
                                                                except:
                                                                    _logger.error('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    send_log('Test d\'existence sql NON BLOQUANT (sauter) de feuille pour l\'utilisateur %s échoué'%user_id)
                                                                    pass

                                                                #if the employe is deactivated (non-active)
                                                                if str(etat_active_employe) == '0':
                                                                    ready_for_create = False

                                                                #the timesheet is already confirmed
                                                                if hr_timesheet_sheet_dt and len(hr_timesheet_sheet_dt)>0 :
                                                                    for timesheet_line in hr_timesheet_sheet_dt:
                                                                        if timesheet_line:
                                                                            timesheet_id, timesheet_state = timesheet_line
                                                                            if timesheet_state == 'done':
                                                                                ready_for_create_2 = False
                                                                                break                                                                

                                                                #_____________________________________________________________________________________|

                                                                # THEN, IF THE SHEET FOR THE USER_ID and THE DATE already exist: don't recreate line
                                                                id_bodir_controle = analytic_line_obj.search(cr, uid, ['&',('bodir_controle_id','=',id_controle),('bodir_controle_agent_id','=',id_controle_agent)])
                                                                if not id_bodir_controle:
                                                                    try:
                                                                        if ready_for_create_1:
                                                                            creating_1 = analytic_line_obj.create(cr, uid, analytic_account_line_data_1)
                                                                            print "----> 2nd RULE create status analytic account: %s"%(creating_1)
                                                                        else:
                                                                            send_log('Règle 2, Date présence partie 1 :%s ,ID utilisateur:%s ne peut pas être ajouté car feuille de temps déjà confirmé'%(date_presence_part_1,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('creating_1 dans RULE 2 rencontre un problème.')
                                                                        send_log('creating_1 dans RULE 2 rencontre un problème.')
                                                                        stop_and_change_status()
                                                                    try:
                                                                        if ready_for_create_2:
                                                                            creating_2 = analytic_line_obj.create(cr, uid, analytic_account_line_data_2)
                                                                            print "----> 2nd RULE create status analytic account: %s"%(creating_2)
                                                                        else:
                                                                            send_log('Règle 2, Date présence partie 2 :%s ,ID utilisateur:%s ne peut pas être ajouté car feuille de temps déjà confirmé'%(date_presence_part_2,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('creating_2 dans RULE 2 rencontre un problème.')
                                                                        send_log('creating_2 dans RULE 2 rencontre un problème.')
                                                                        stop_and_change_status()
                                                                    
                                                                else:
                                                                    #line already exist so UPDATE line
                                                                    """
                                                                    try:
                                                                        if ready_for_create_1:
                                                                            updating_1 = analytic_line_obj.write(cr, uid,id_bodir_controle, analytic_account_line_data_1)
                                                                            print "----> 2nd RULE update status analytic account: %s"%(updating_1)
                                                                        else:
                                                                            send_log('Règle 2, Date présence partie 1 :%s ,ID utilisateur:%s ne peut pas être mis à jour car feuille de temps déjà confirmé'%(date_presence_part_1,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('updating_1 dans RULE 2 rencontre un problème.')
                                                                        send_log('updating_1 dans RULE 2 rencontre un problème.')
                                                                        stop_and_change_status()
                                                                    try:
                                                                        if ready_for_create_2:
                                                                            updating_2 = analytic_line_obj.write(cr, uid,id_bodir_controle, analytic_account_line_data_2)
                                                                            print "----> 2nd RULE update status analytic account: %s"%(updating_2)
                                                                        else:
                                                                            send_log('Règle 2, Date présence partie 2 :%s ,ID utilisateur:%s ne peut pas être mis à jour car feuille de temps déjà confirmé'%(date_presence_part_2,user_id),'INFO')
                                                                    except:
                                                                        _logger.error('updating_2 dans RULE 2 rencontre un problème.')
                                                                        send_log('updating_2 dans RULE 2 rencontre un problème.')
                                                                        stop_and_change_status() 
                                                                    """


                                                                    _logger.info(u"La ligne de controle RULE 2, %s existe déjà dans 'account_analytic_line'."%id_bodir_controle)
                                                                    send_log(u"La ligne de controle RULE 2, %s existe déjà dans 'account_analytic_line'."%id_bodir_controle,"INFO")
                                                        else:
                                                            _logger.info(u"!!! LA VALEUR DE L'HEURE DE CONTROLE EST %s"%(controle_hour))
                                                            send_log(u"!!! LA VALEUR DE L'HEURE DE CONTROLE EST %s"%(controle_hour),"INFO")

                                            else:
                                                _logger.info(u"Pas de type de présence trouvé pour le type nuit. Doit être: 'Travail de Nuit'.")
                                                send_log(u"Pas de type de présence trouvé pour le type nuit. Doit être: 'Travail de Nuit'.","INFO")

                # update status of cron : en cours > False
                else:
                #if cron_timesheet_obj.search(cr, uid, [('only_one','=','1')])>0:
                    _logger.info(u"Pas de controle trouvé pour hier ou cas entre la date spécifiée dans la configuration (s'il y en a) et aujourd'hui.")
                    send_log(u"Pas de controle trouvé pour hier ou cas entre la date spécifiée dans la configuration (s'il y en a) et aujourd'hui.","INFO")
                    
                    #maj = cron_timesheet_obj.write(cr, uid,id_cron, {'cron_state':'False'})
                    cr.execute("update dirickx_remote_db set cron_state = False")
                    cr.commit()
                    #print "maj:",maj

            except:
                # update status of cron : en cours > False
                cr = self.env.cr; uid= self.env.uid                
                cron_timesheet_obj = self.pool.get('dirickx.remote.db')
                id_cron = cron_timesheet_obj.search(cr, uid, [('only_one','=','1')])
                if id_cron:
                    cr.execute("update dirickx_remote_db set cron_state = False")
                    cr.commit()

                _logger.error(u'Une erreur est survenue pendant le CRON.')
                send_log(u'Une erreur est survenue pendant le CRON.\nNiveau principal.')
                return False


                #print "Date: %s, clé controlleur: %s, site: %s, token: %s" %(debut_controle,fk_controlleur,fk_site,token)


        """
        __________________________________________________________________________________________

        @Description : FUNCTION FOR CREATING AUTO TIMESHEETS
        @Author: Lanto RAZAFINDRABE
        @Begins on : 26/12/2016
        __________________________________________________________________________________________

        """
        #odoo cron for auto create timesheet monthly of each user

        @api.model
        def create_timesheet_auto(self):
            
            """
            ----------------------------------
            TRIGGERED by PLANIFICATEUR IN ODOO
            ----------------------------------

            for having the current month in the date format 2016-08-18 14:17:36.811000
            str(datetime.datetime.now()).split(' ')[0].split('-')[1] ==> we got "08"
            
            OR 
            
            do with this code
            import datetime
            mydate = datetime.datetime.now()
            mydate.strftime("%B") #return "August"

            """

            cr = self.env.cr; uid= self.env.uid

            #function to push all log to DB
            def send_log(log_content = None,type_log='ERROR'):
                    log_cron_obj = self.pool.get('log.dirickx.db')
                    log_data = {
                        'log_content':log_content,
                        'type_log': type_log,
                        'date_log':str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]),
                        }                                    
                    log_cron_obj.create(cr, uid, log_data)

            _logger.info(">----- CRON AUTO CREATE TIMESHEETS ----<")
            sheet_obj = self.pool.get('hr_timesheet_sheet.sheet')
            employee_obj = self.pool.get('hr.employee')             
            #HERE FOR THE LOOP FOR ALL employee AND testing the month date_to with the current date.
            ids = employee_obj.search(cr, uid,[('id', '>', 0)]) #here if adding some criteria for the automatic creation of timesheet
            if ids:
                # actually if one of all generated timesheet is deleted, this will not be restored [NOT IN CONDITION IF]
                for line in employee_obj.browse(cr, uid, ids):
                    """ structure of data got by printed vals in hr_timesheet_sheet >> hr_timesheet_sheet.py ||at def create on line 66 """

                    today = datetime.date.today()
                    firstCurrentMonth = today.replace(day=1)
                    lastMonth = firstCurrentMonth - datetime.timedelta(days=1)

                    data_obj = {'date_from': str(lastMonth)[0:7]+'-20','date_to': str(firstCurrentMonth)[0:7]+'-19','department_id': False,'message_follower_ids': False, 'timesheet_ids': [], 'employee_id': line.id, 'name': False,  'attendances_ids': [], 'company_id': 1, 'message_ids': False, 'department_id': False}
                    
                    #>>>> type of data if restore from a date we want to create: 
                    #{'message_follower_ids': False, 'timesheet_ids': [], 'employee_id': 40, 'name': False, 'date_from': '2016-08-01', 'attendances_ids': [], 'company_id': 1, 'date_to': '2016-08-31', 'message_ids': False, 'department_id': False}
                    
                    now = datetime.datetime.now()
                    first_month_current_date = str(now.strftime("%Y-%m"))+'-01'             
                    if not sheet_obj.search(cr,uid,['&',('employee_id','=',line.id),('date_from','=',str(lastMonth)[0:7]+'-20')]):
                        try: 
                            sheet_obj.create(cr,uid,data_obj)
                        except:             
                            #print ("Duplicated of record but not too similar, or employee not in res.users (no user related with it) :: log by Lanto. \n==> ID on hr.employee:"+str(line.id)+", NAME:"+str(line.name_related))
                            _logger.info("\n\nDuplicated of record but not too similar, or employee not in res.users (no user related with it). \n==> ID on hr.employee:"+str(line.id))
                            send_log("ERREUR à la création de la feuilles de temps AUTO: qui peut être Enregistrement dupliqué mais pas totalement identique , ou l'employé n'a pas d'utilisateur lié \n==> ID SUR hr.employee:"+str(line.id),"INFO")
                            #self._logger.info("\nNAME:"+str(line.name_related))
                    else:
                        _logger.info("\n\nDuplicated of record . \n==> ID on hr.employee:"+str(line.id))
                        send_log("Feuilles de temps AUTO: Enregistrement dupliqué ou intervalle existant se chevauchant avec l'un en cours.\n==> ID sur hr.employee:"+str(line.id),"INFO")