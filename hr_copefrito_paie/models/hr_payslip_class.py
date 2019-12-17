# -*- coding: utf-8 -*-

from openerp import models, api, fields


class HrPayslipClass(models.Model):
    _name = 'hr.payslip.class'
    _order = 'code'

    @api.one
    def _get_name(self):
        if self.class_conf_id:
            self.name = self.class_conf_id.name

    @api.returns('self')
    def _default_stage(self):
        return self.env['hr.payslip.state'].search([], limit=1)

    def domain_rubric(self):
        #        print _id
        #        lambda self, self.id: self.domain_rubric(sel)
        return [('id', '=', [1, 2, 3, 4])]

    payslip_run = fields.Many2one("hr.payslip.run", u"Période de paie")
    class_conf_id = fields.Many2one("hr.payslip.class.config", "Classe")
    rubric_ids = fields.One2many("hr.payslip.rubric", "class_id", string=u"Rubriques")
    name = fields.Char("Nom", compute=_get_name)
    code = fields.Char("Code", related="class_conf_id.code", store=True)
    nb_rubrics = fields.Integer('Nombre de rubriques', compute='_compute_nb_rubrics')
    state = fields.Selection(
        [('draft', 'Brouillon'), ('pending', 'En cours'), ('instance', 'Instance'), ('validate', u'Validé'),
         ('closed', u'Clôturé'), ('neutre', 'Neutre')], 'Etat', default='draft', compute='_compute_state', store=True)
    nb_rubrics_draft = fields.Integer(u'Nombre de rubriques brouillons', compute='_compute_nb_rubrics')
    nb_rubrics_pending = fields.Integer(u'Nombre de rubriques en cours', compute='_compute_nb_rubrics')
    nb_rubrics_instance = fields.Integer(u'Nombre de rubriques en instances', compute='_compute_nb_rubrics')
    nb_rubrics_validate = fields.Integer(u'Nombre de rubriques validées', compute='_compute_nb_rubrics')
    nb_rubrics_closed = fields.Integer(u'Nombre de rubriques clôturées', compute='_compute_nb_rubrics')
    slip_line_ids = fields.One2many("hr.payslip.line", string=u"Lignes de paies", compute="_get_slip_lines")
    service = fields.Many2many('hr.department', 'department_class_rel', 'class_id', 'department_id', 'Service')
    matricule = fields.Many2many('hr.employee', 'employee_class_rel', 'class_id', 'employee_id', 'Matricule')
    active = fields.Boolean(string=u"Active", default=True)

    @api.one
    @api.onchange('service', 'matricule')
    def on_change_filter(self):
        self._get_slip_lines()
        line_ids = self.slip_line_ids

        if self.service:
            line_ids = line_ids.filtered(lambda r: r.employee_id.department_id in self.service)

        if self.matricule:
            line_ids = line_ids.filtered(lambda r: r.employee_id in self.matricule)

        self.slip_line_ids = line_ids

        return True

    @api.multi
    def _get_slip_lines(self):
        for classe in self:
            line_ids = self.env['hr.payslip.line'].browse([])
            for rubric in classe.rubric_ids:
                line_ids += rubric.line_ids
            classe.slip_line_ids = line_ids

    @api.one
    @api.depends('rubric_ids')
    def _compute_nb_rubrics(self):
        self.nb_rubrics = len(self.rubric_ids)
        self.nb_rubrics_draft = len(self.rubric_ids.filtered(lambda c: c.state == 'draft'))
        self.nb_rubrics_pending = len(self.rubric_ids.filtered(lambda c: c.state == 'pending'))
        self.nb_rubrics_instance = len(self.rubric_ids.filtered(lambda c: c.state == 'instance'))
        self.nb_rubrics_validate = len(self.rubric_ids.filtered(lambda c: c.state == 'validate'))
        self.nb_rubrics_closed = len(self.rubric_ids.filtered(lambda c: c.state == 'closed'))

    @api.one
    @api.depends('rubric_ids.state')
    def _compute_state(self):
        # all rubric_ids is in draft
        if (all(st.state == 'draft' for st in self.rubric_ids)):
            self.state = 'draft'

        # all rubric_ids is in neutre
        if (all(st.state == 'neutre' for st in self.rubric_ids)):
            self.state = 'neutre'

        # at least one rubric is in pending
        elif (any(st.state == 'pending' for st in self.rubric_ids)):
            self.state = 'pending'

        # at least one rubric is in instance and there is no rubric in draft or pending
        elif (any(st.state == 'instance' for st in self.rubric_ids) and not (
                any(st.state == 'draft' or st.state == 'pending' for st in self.rubric_ids))):
            self.state = 'instance'

        # all rubric_ids is validate or neutre
        elif (all(st.state == 'validate' or st.state == 'neutre' for st in self.rubric_ids)):
            self.state = 'validate'

        # all rubric_ids are in draft or neutre (there should be at least one rubric in draft)
        elif (all(st.state == 'draft' or st.state == 'neutre' for st in self.rubric_ids)):
            self.state = 'draft'
        else:
            self.state = 'pending'

        # Class' state closed
        if (all(st.state == 'closed' for st in self.rubric_ids)):
            self.state = 'closed'

    @api.one
    def toggle_button_state(self):
        self.button_state = not self.button_state

    @api.one
    def change_color(self):
        if not self.color_button or self.color_button == 'grey':
            self.color_button = 'green'
        else:
            self.color_button = 'grey'

    @api.multi
    def colorize_orange(self):
        return True

    @api.multi
    def write(self, vals):
        if vals.has_key('matricule'): del vals['matricule']
        if vals.has_key('service'): del vals['service']
        res = super(HrPayslipClass, self).write(vals)
        return res

    @api.multi
    def view_class(self):
        '''
        This function returns view form for model Class.
        '''
        return {
            'name': 'lasse',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payslip.class',
            'view_id': self.env.ref('hr_copefrito_paie.hr_payslip_class_form_view').id,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'current'
        }


class HrPayslipClassConfirm(models.Model):
    _name = 'hr.payslip.class.confirm'
    _description = u"Confirmation des classes selectionnées"

    @api.multi
    def classes_confirm(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        active_model = context.get('active_model')

        for record in self.env[active_model].browse(active_ids):
            employee_name = record.employee_id.name.encode("utf-8")
            body_html = "<p>Matricule: " + str(record.matricule) + "<br/>Employé: " + employee_name + "<ul>"
            if record.color_button != 'orange':
                old_color = "Vérifié" if record.color_button == 'green' else "Brouillon"
                body_html += "<li>Etat: %s &rarr; Mise en attente</li></ul></p>" % (old_color)
            record.color_button = 'orange'
            record.rubric_id.message_post(body=body_html, subtype='mail.mt_note')
        return {'type': 'ir.actions.act_window_close'}
