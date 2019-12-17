# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2019 eTech (<https://www.etechconsulting-mg.com/>). All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from openerp import models, api, fields
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from cookielib import vals_sorted_by_key
import werkzeug
from urlparse import urljoin
import openerp.addons.decimal_precision as dp

from openerp.exceptions import ValidationError
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class one2many_mod2(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        if not values:
            values = {}
        res = {}
        for id in ids:
            res[id] = []
        ids2 = obj.pool[self._obj].search(cr, user, [(self._fields_id, 'in', ids), ('appears_on_payslip', '=', True),
                                                     ('slip_id.state', 'not in', ['cancel'])],
                                          limit=self._limit)
        for r in obj.pool[self._obj].read(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            key = r[self._fields_id]
            if isinstance(key, tuple):
                # Read return a tuple in the case where the field is a many2one
                # but we want to get the id of this field.
                key = key[0]

            res[key].append(r['id'])
        return res


class one2many_mod3(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        if not values:
            values = {}
        res = {}
        for id in ids:
            res[id] = []
        current_user = obj.pool['res.users'].browse(cr, user, user)
        service_ids = current_user.service_ids.ids
        csp_ids = current_user.csp_ids.ids
        domain = [(self._fields_id, 'in', ids), ('payslip_id.state', '!=', 'cancel')]
        context = self._context
        pay_operator_model, pay_operator_group = obj.pool.get('ir.model.data').get_object_reference(cr, user,
                                                                                                    'hr_copefrito_paie',
                                                                                                    'group_pay_operateur')

        pay_operator_users = obj.pool.get('res.groups').browse(cr, user, pay_operator_group).users.ids

        system_admin_model, system_admin_group = obj.pool.get('ir.model.data').get_object_reference(cr, user,
                                                                                                    'hr_copefrito_paie',
                                                                                                    'group_system_admin')
        system_admin_users = obj.pool.get('res.groups').browse(cr, user, system_admin_group).users.ids

        pay_manager_model, pay_manager_group = obj.pool.get('ir.model.data').get_object_reference(cr, user,
                                                                                                  'hr_copefrito_paie',
                                                                                                  'group_pay_manager')

        pay_manager_users = obj.pool.get('res.groups').browse(cr, user, pay_manager_group).users.ids

        if current_user.id in pay_operator_users and current_user.id not in system_admin_users and current_user.id not in pay_manager_users:
            # if user != SUPERUSER_ID:
            #     # domain += [('employee_id.department_id', 'in', service_ids), ('employee_id.csp_id', 'in', csp_ids)]
            domain += ['|', ('employee_id.csp_id.is_hc', '=', False), ('employee_id.csp_id', '=', False)]
        ids2 = obj.pool[self._obj].search(cr, SUPERUSER_ID, domain, limit=self._limit)
        for r in obj.pool[self._obj].read(cr, SUPERUSER_ID, ids2, [self._fields_id], context=context,
                                          load='_classic_write'):
            key = r[self._fields_id]
            if isinstance(key, tuple):
                # Read return a tuple in the case where the field is a many2one
                # but we want to get the id of this field.
                key = key[0]

            res[key].append(r['id'])
        return res


class related_mod2(fields.related):
    """
        new type of fields which inherit fields.related
        it creates a filter for user who are not admin
        only hr.payslip.input of employee with service which matched with service_ids of current user
    """

    def _related_read(self, obj, cr, uid, ids, field_name, args, context=None):
        current_user = obj.pool['res.users'].browse(cr, uid, uid)
        service_ids = current_user.service_ids.ids
        csp_ids = current_user.csp_ids.ids
        res = super(related_mod2, self)._related_read(obj, cr, uid, ids, field_name, args, context)
        is_operator = current_user.has_group('hr_copefrito_paie.group_pay_operateur')
        is_manager = current_user.has_group('hr_copefrito_paie.group_pay_manager')
        if not is_operator:
            for id in ids:
                rec_ids = obj.pool[self._obj].search(cr, SUPERUSER_ID, [('id', 'in', res[id]), (
                    'employee_id.department_id', 'in', service_ids), ('employee_id.csp_id', 'in', csp_ids)])
                res[id] = rec_ids
        elif not is_manager:
            for id in ids:
                rec_ids = obj.pool[self._obj].search(cr, SUPERUSER_ID, [('id', 'in', res[id]), '|',
                                                                        ('employee_id.csp_id.is_hc', '=', False),
                                                                        ('employee_id.csp_id', '=', False)])
                res[id] = rec_ids
        # if uid != SUPERUSER_ID:
        #     for id in ids:
        #         rec_ids = obj.pool[self._obj].search(cr, SUPERUSER_ID, [('id', 'in', res[id]), (
        #         'employee_id.department_id', 'in', service_ids), ('employee_id.csp_id', 'in', csp_ids)])
        #         res[id] = rec_ids
        return res


class HrPayslipRubric(osv.osv):
    _name = 'hr.payslip.rubric'
    _description = 'Rubric in payslip lines'
    _order = 'code'
    _inherit = ['mail.thread']

    def on_change_filter(self, cr, uid, ids, service_ids, matricule_ids, context=None):
        dom_mat = matricule_ids[0][2] if matricule_ids and matricule_ids[0] and matricule_ids[0][2] else []
        op_mat = 'in' if matricule_ids and matricule_ids[0] and matricule_ids[0][2] else 'not in'
        dom_ser = service_ids[0][2] if service_ids and service_ids[0] and service_ids[0][2] else []
        op_ser = 'in' if service_ids and service_ids[0] and service_ids[0][2] else 'not in'

        hpl_pool = self.pool.get('hr.payslip.line')
        hpi_pool = self.pool.get('hr.payslip.input')

        if not ids:
            line_ids_filter = hpl_pool.search(cr, uid, [
                ('rubric_id', '=', 0),
                ('employee_id', op_mat, dom_mat),
                ('employee_id.department_id', op_ser, dom_ser),
            ], None)
            input_ids_filter = hpi_pool.search(cr, uid, [
                ('rubric_id', '=', 0),
                ('contract_id.employee_id', op_mat, dom_mat),
                ('contract_id.employee_id.department_id', op_ser, dom_ser),
            ])

        else:
            line_ids_filter = hpl_pool.search(cr, uid, [
                ('rubric_id', '=', ids[0]),
                ('employee_id', op_mat, dom_mat),
                ('employee_id.department_id', op_ser, dom_ser),
            ], None)
            input_ids_filter = hpi_pool.search(cr, uid, [
                ('rubric_id', '=', ids[0]),
                ('contract_id.employee_id', op_mat, dom_mat),
                ('contract_id.employee_id.department_id', op_ser, dom_ser),
            ], None)
        return {
            'value': {
                'line_ids': [(6, 0, line_ids_filter)],
                'input_ids': [(6, 0, input_ids_filter)],
            }
        }

    def _inputs_count(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        # result[rubric_id.id] = len(rubric_id.input_ids.ids)
        for rub in rubric_id:
            result[rub.id] = len(rub.input_ids.ids)
        return result

    def _inputs_count_draft(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        # result[rubric_id.id] = len(rubric_id.input_ids.filtered(lambda c: c.color_button == 'grey'))
        for rub in rubric_id:
            result[rub.id] = len(rub.input_ids.filtered(lambda c: c.color_button == 'grey'))
        return result

    def _inputs_count_waiting(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        for rub in rubric_id:
            result[rub.id] = len(rub.input_ids.filtered(lambda c: c.color_button == 'orange'))
        # result = {}
        # print rubric_id
        # result[rubric_id.id] = len(rubric_id.input_ids.filtered(lambda c: c.color_button == 'orange'))
        return result

    def _inputs_count_verified(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        # result[rubric_id.id] = len(rubric_id.input_ids.filtered(lambda c: c.color_button == 'green'))
        for rub in rubric_id:
            result[rub.id] = len(rub.input_ids.filtered(lambda c: c.color_button == 'green'))
        return result

    def open_input_ids(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        domain = [('id', '=', rubric_id.input_ids.ids)]
        return {
            'type': 'ir.actions.act_window',
            'name': u'Entrées',
            'res_model': 'hr.payslip.input',
            'view_type': 'form',
            'view_mode': 'tree',
            'domain': domain,
        }

    def open_line_ids(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        domain = [('id', '=', rubric_id.line_ids.ids)]
        ir_model_obj = self.pool['ir.model.data']
        model, view_id = ir_model_obj.get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                           'view_hr_payslip_line_tree_inherit')
        return {
            'type': 'ir.actions.act_window',
            'name': u'Résultats',
            'res_model': 'hr.payslip.line',
            'view_type': 'form',
            'view_mode': 'tree',
            'domain': domain,
            'view_id': view_id
        }

    def open_rubric_tree(self, cr, uid, ids, context):
        model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'group_pay_manager')
        user_admins = self.pool.get('res.groups').browse(cr, uid, model_id).users.ids
        current_user = self.pool.get('res.users').browse(cr, uid, uid)
        # if the current_user is an admin
        # if current_user.id in user_admins:
        #     domain = [(('payslip_run.company_id.id', 'in', current_user.company_ids.ids))]
        # # if the current_user is not an admin
        # else:
        #     rub_conf_data = self.pool.get('operator.card').search(cr, uid, [('user_id.id', '=', uid)], None)
        #     rub_list = []
        #     for r in self.pool.get('operator.card').browse(cr, uid, rub_conf_data):
        #         rub_list += r.rubric_ids.ids
        #     user_company_id = current_user.company_id.id
        #     domain = [('paylip_rubric_conf_id.id', 'in', rub_list), ('payslip_run.company_id.id', '=', user_company_id)]
        #     domain.append(('state', 'in', ['draft', 'pending', 'instance']))
        domain = [(('payslip_run.company_id.id', 'in', current_user.company_ids.ids))]
        return {
            'type': 'ir.actions.act_window',
            'name': u'Rubriques',
            'res_model': 'hr.payslip.rubric',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': domain,
            # 'context':"{'search_default_group_payslip_run': 1, 'search_default_group_payslip_run_classe': 1, 'search_default_filter_rub_draft':1, 'search_default_filter_rub_pending':1, 'search_default_filter_rub_instance':1,}"
            'context': "{'search_default_group_payslip_run': 1, 'search_default_group_payslip_run_classe': 1}"
        }

    def make_rectified(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        is_pending = False
        ctx = dict(context or {})
        ctx['from_button'] = True
        for input_id in rubric_id.input_ids:
            if input_id.color_button == 'green':
                self.pool.get('hr.payslip.input').change_color(cr, uid, input_id.id, context=ctx)
            else:
                is_pending = True
        rubric_id.state = 'draft' if not is_pending else 'pending'

        rubric_id.message_post(body="<p>Tous les entrées sont mises à l'état <strong>Brouillon</strong></p>",
                               subtype='mail.mt_note')

    def make_verified(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        ctx = dict(context or {})
        ctx['from_button'] = True
        for input_id in rubric_id.input_ids:
            name = input_id.name_employee_id
            if input_id.color_button == 'orange': input_id.color_button = 'grey'
            if input_id.color_button != 'green':
                self.pool.get('hr.payslip.input').change_color(cr, uid, input_id.id, context=ctx)
        rubric_id.state = 'pending'

        rubric_id.message_post(body="<p>Toutes les entrées sont mises à l'état <strong>Vérifié</strong></p>",
                               subtype='mail.mt_note')

    def submit_input_ids(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        mail_mail_obj = self.pool.get('mail.mail')
        mail_template_obj = self.pool.get('mail.template')
        model, template = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'email_template_notification_payslip_rubric_to_validate')
        values = mail_template_obj.generate_email(cr, uid, template, rubric_id.id, context=context)
        values['email_from'] = self.pool.get('res.users').browse(cr, uid, uid).company_id.email
        model, group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'group_pay_manager')
        user_responsables = self.pool.get('res.groups').browse(cr, uid, group_id).users
        responsable_ids = filter(lambda res: res.company_id == rubric_id.payslip_run.company_id, user_responsables)
        recipient_ids = [(4, recp_id.partner_id.id) for recp_id in responsable_ids]
        values['recipient_ids'] = recipient_ids
        msg_id = mail_mail_obj.create(cr, uid, values, context=context)

        # send mail
        if msg_id:
            mail_mail_obj.send(cr, uid, [msg_id], context=context)
        rubric_id.state = 'instance'

        # odoo notification
        mail_thread = self.pool.get('mail.thread')
        mail_thread.message_post(cr, uid, False, type="notification", subtype="mt_comment", context=context,
                                 body=values['body'], partner_ids=recipient_ids)

    def back_to_instance(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        rubric_id.state = 'instance'

    def _rectify_visibility(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        condition = any(input_id.color_button == 'green' or input_id.color_button == 'orange' for input_id in
                        rubric_id.input_ids) and rubric_id.state in ['draft', 'pending', 'instance']
        result[rubric_id.id] = condition if rubric_id.state in ['draft',
                                                                'pending'] else condition and rubric_id.is_operator_input
        return result

    def _verify_visibility(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        result[rubric_id.id] = any(input_id.color_button == 'grey' or input_id.color_button == 'orange' for input_id in
                                   rubric_id.input_ids) and rubric_id.state in ['draft', 'pending']
        return result

    def _submit_visibility(self, cr, uid, ids, field_name, arg, context=None):
        # have to specify the user as SUPERUSER for consistency of the button's visibility

        # uid = SUPERUSER_ID
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        result[rubric_id.id] = all(
            input_id.color_button == 'green' for input_id in rubric_id.input_ids) and rubric_id.state in ['draft',
                                                                                                          'pending']
        return result

    def compute_is_operator_input(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        result = {}
        model, group_pay_manager = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                                       'group_pay_manager')
        model, group_pay_operateur = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                                         'group_pay_operateur')
        pay_manager_users = self.pool.get('res.groups').browse(cr, uid, group_pay_manager).users.ids
        pay_operateur_users = self.pool.get('res.groups').browse(cr, uid, group_pay_operateur).users.ids
        op_pure = list(set(pay_operateur_users).difference(pay_manager_users))
        if uid in op_pure:
            result[rubric_id.id] = True
        else:
            result[rubric_id.id] = False
        return result

    def compute_total_amount_line_ids(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        rubric_id = self.browse(cr, uid, ids)[0]
        result[rubric_id.id] = sum(line.total for line in rubric_id.line_ids.filtered(lambda x: x.appears_on_payslip))
        return result

    def compute_total_amount_input_ids(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        rubric_id = self.browse(cr, uid, ids)[0]
        result[rubric_id.id] = sum(line.amount2 for line in rubric_id.input_ids)
        return result

    def make_validate(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        if not rubric_id.class_id.payslip_run.computed_payslips:
            raise ValidationError(_('Please compute the period : %s') % rubric_id.class_id.payslip_run.name)
        if any(input_id.color_button != 'green' for input_id in rubric_id.input_ids):
            rubric_id.make_verified()
        rubric_id.state = 'validate'
        mail_mail_obj = self.pool.get('mail.mail')
        mail_template_obj = self.pool.get('mail.template')
        model, template = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'email_template_notification_payslip_rubric_is_validated')
        values = mail_template_obj.generate_email(cr, uid, template, rubric_id.id, context=context)
        values['email_from'] = self.pool.get('res.users').browse(cr, uid, uid).company_id.email
        model, group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'group_pay_manager')
        user_responsables = self.pool.get('res.groups').browse(cr, uid, group_id).users
        responsable_ids = filter(lambda res: res.company_id == rubric_id.payslip_run.company_id, user_responsables)
        recipient_ids = [(4, recp_id.partner_id.id) for recp_id in responsable_ids]
        values['recipient_ids'] = recipient_ids
        msg_id = mail_mail_obj.create(cr, uid, values, context=context)

        # send mail
        if msg_id:
            mail_mail_obj.send(cr, uid, [msg_id], context=context)
        rubric_id.message_post(body="<p>Rubrique validée</p>", subtype='mail.mt_note')

        # odoo notification
        mail_thread = self.pool.get('mail.thread')
        mail_thread.message_post(cr, uid, False, type="notification", subtype="mt_comment", context=context,
                                 body=values['body'], partner_ids=recipient_ids)

    def make_refused(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        is_pending = False
        for input_id in rubric_id.input_ids:
            if input_id.payslip_id.state not in ['validate', 'waiting', 'done', 'cancel']:
                input_id.color_button = 'grey'
            else:
                is_pending = True
        rubric_id.state = 'draft' if not is_pending else 'pending'
        rubric_id.message_post(body="<p>La validation de la rubrique a été refusée</p>", subtype='mail.mt_note')

    def make_draft(self, cr, uid, ids, context):
        rubric_id = self.browse(cr, uid, ids)
        # for input_id in rubric_id.input_ids:
        rubric_id.state = 'draft'

    def _get_current_url(self, cr, uid, ids, field_name, arg, context=None):
        rubric_id = self.browse(cr, uid, ids)
        get_param = self.pool['ir.config_parameter'].get_param
        base_url = get_param(cr, SUPERUSER_ID, 'web.base.url', context=context)
        fragment = dict()
        base = '/web#'
        fragment['id'] = rubric_id.id
        fragment['view_type'] = 'form'
        fragment['model'] = 'hr.payslip.rubric'
        result = {}
        result[rubric_id.id] = urljoin(base_url, base + werkzeug.url_encode(fragment))
        return result

    _columns = {
        'payslip_run': fields.many2one("hr.payslip.run", u"Période de paie"),
        'paylip_rubric_conf_id': fields.many2one("hr.payslip.rubric.config", "Rubrique"),
        'line_ids': one2many_mod2('hr.payslip.line', 'rubric_id', 'Details calcul'),
        'input_ids': one2many_mod3('hr.payslip.input', 'rubric_id', string=u"Entrées de paie"),
        'input_ids_2': related_mod2('input_ids', relation='hr.payslip.input', type='one2many',
                                    string=u'Entrées de paie'),
        # 'code' : fields.related('paylip_rubric_conf_id', 'code', type='integer', string=u'Code', readonly=True, store=True, group_operator=False),
        'code': fields.related('paylip_rubric_conf_id', 'code', type='char', string=u'Code', readonly=True, store=True,
                               group_operator=False),
        'class_id': fields.many2one("hr.payslip.class", "Classe"),
        'responsable_ids': fields.related("paylip_rubric_conf_id", "responsable_ids", type='many2many',
                                          relation='res.users', string=u"Responsable", readonly=True),
        'service': fields.many2many('hr.department', 'department_rubric_rel', 'rubric_id', 'department_id', 'Service'),
        'matricule': fields.many2many('hr.employee', 'employee_rubric_rel', 'rubric_id', 'employee_id', 'Matricule'),
        'nb_input': fields.function(_inputs_count, type='integer', string=u'Nombre d\'entrées'),
        'state': fields.selection(
            [('draft', 'Brouillon'), ('pending', 'En cours'), ('instance', 'Instance'), ('validate', u'Validé'),
             ('closed', u'Clôturé'), ('neutre', u'Neutre')], 'Etat', track_visibility='onchange'),
        'nb_input_draft': fields.function(_inputs_count_draft, type='integer', string=u'Nombre d\'entrées brouillons',
                                          track_visibility='always'),
        'nb_input_waiting': fields.function(_inputs_count_waiting, type='integer',
                                            string=u'Nombre d\'entrées mise en attente', track_visibility='always'),
        'nb_input_verified': fields.function(_inputs_count_verified, type='integer',
                                             string=u'Nombre d\'entrées vérifiées', track_visibility='always'),
        'button_rectify_visible': fields.function(_rectify_visibility, type='boolean'),
        'button_verify_visible': fields.function(_verify_visibility, type='boolean'),
        'button_submit_visible': fields.function(_submit_visibility, type='boolean'),
        'current_url': fields.function(_get_current_url, type='char', string=u'url'),
        'is_operator_input': fields.function(compute_is_operator_input, type='boolean'),
        'rubric_conf_name': fields.related('paylip_rubric_conf_id', 'name', type='char', string=u'Rubrique',
                                           readonly=True),
        'active': fields.boolean(string=u"Active"),
        'invisible_qty': fields.related('paylip_rubric_conf_id', 'invisible_qty', type='boolean',
                                        string=u'Ne pas afficher', readonly=True),
        'total_amount_input_ids': fields.function(compute_total_amount_input_ids, type='float', string=u'Total'),
        'total_amount_line_ids': fields.function(compute_total_amount_line_ids, type='float', string=u'Total'),
    }

    _defaults = {
        'state': 'draft',
        'active': True,
    }

    _rec_name = 'rubric_conf_name'

    def write(self, cr, uid, ids, vals, context=None):
        if vals.has_key('matricule'): del vals['matricule']
        if vals.has_key('service'): del vals['service']
        self.on_change_filter(cr, uid, ids, [], [])
        if vals.has_key('input_ids'):
            for res in vals['input_ids']:
                if res[0] == 2:
                    res[0] = 4

        res = super(HrPayslipRubric, self).write(cr, uid, ids, vals)
        return res

    def view_rubrique(self, cr, uid, ids, context=None):
        '''
        This function returns view form for model Rubric.
        '''
        model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'hr_copefrito_paie',
                                                                              'hr_payslip_rubric_view_form')
        return {
            'name': 'Rubrique',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payslip.rubric',
            'view_id': model_id,
            'type': 'ir.actions.act_window',
            'res_id': ids[0],
            'target': 'current'
        }

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False,
                   lazy=True):
        '''
            This function replace the old function in order to not display code in sum in group by.
        '''
        if context is None:
            context = {}
        self.check_access_rights(cr, uid, 'read')
        query = self._where_calc(cr, uid, domain, context=context)
        fields = fields or self._columns.keys()

        groupby = [groupby] if isinstance(groupby, basestring) else groupby
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [
            self._read_group_process_groupby(cr, uid, gb, query, context=context)
            for gb in groupby_list
        ]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(cr, uid, query, 'read', context=context)
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            groupby_def = self._columns.get(gb) or (self._inherit_fields.get(gb) and self._inherit_fields.get(gb)[2])
            assert groupby_def and groupby_def._classic_write, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
            if not (gb in self._fields):
                # Don't allow arbitrary values, as this would be a SQL injection vector!
                raise UserError(_(
                    'Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.') % (
                                    gb,))

        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence', 'code')
            if f not in groupby_fields
            if f in self._fields
            if self._fields[f].type in ('integer', 'float', 'monetary')
            if getattr(self._fields[f].base_field.column, '_classic_write', False)
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator or 'None',
            self._inherits_join_calc(cr, uid, self._table, f, query, context=context),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(cr, uid, order, aggregated_fields, annotated_groupbys,
                                                                query, context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.id) AS id, count(%(table)s.id) AS %(count_field)s %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        cr.execute(query, where_clause_params)
        fetched_data = cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        many2onefields = [gb['field'] for gb in annotated_groupbys if gb['type'] == 'many2one']
        if many2onefields:
            data_ids = [r['id'] for r in fetched_data]
            many2onefields = list(set(many2onefields))
            data_dict = {d['id']: d for d in self.read(cr, uid, data_ids, many2onefields, context=context)}
            for d in fetched_data:
                d.update(data_dict[d['id']])

        data = map(lambda r: {k: self._read_group_prepare_data(k, v, groupby_dict, context) for k, v in r.iteritems()},
                   fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, groupby_dict, domain, context) for d in
                  data]
        if lazy and groupby_fields[0] in self._group_by_full:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            result = self._read_group_fill_results(cr, uid, domain, groupby_fields[0],
                                                   groupby[len(annotated_groupbys):],
                                                   aggregated_fields, count_field, result, read_group_order=order,
                                                   context=context)

        return result

    def fields_view_get(self, cr, user, view_id=None, view_type=None, context=None, toolbar=False, submenu=False):
        # if context and context.get('opportunity_id'):
        #     action = self.get_formview_action(cr, user, context['opportunity_id'], context=context)
        #     if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
        #         view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(HrPayslipRubric, self).fields_view_get(cr, user, view_id=view_id, view_type=view_type,
                                                           context=context, toolbar=toolbar, submenu=submenu)
        # if view_type == 'form':
        #     res['arch'] = self.fields_view_get_address(cr, user, res['arch'], context=context)
        return res
