# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools
import openerp.addons.decimal_precision as dp
import unicodedata, re
from lxml import etree

try:
    import cStringIO as StringIO
except ImportError:
    import StringIO

from PIL import Image

Payroll = dp.get_precision('Payroll')


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.multi
    def set_default_country(self):
        return self.env.ref('base.mg')

    seuil_irsa = fields.Float('Seuil IRSA', digits_compute=Payroll)
    taux_irsa = fields.Float(u'Taux IRSA (%)', digits_compute=Payroll)
    abat_irsa = fields.Float('Abattement IRSA', digits_compute=Payroll)
    cotisation_cnaps_patr = fields.Float(u'Cotisation Patronale CNAPS (%)',
                                         digits_compute=Payroll)
    cotisation_cnaps_emp = fields.Float(u'Cotisation Employé CNAPS (%)',
                                        digits_compute=Payroll)
    plafond_cnaps = fields.Float(u'Plafond CNAPS',
                                 digits_compute=Payroll)
    # cotisation_sante_patr = fields.Float(u'Cotisation Patronale Santé (%)',
    #                                      digits_compute=Payroll)
    # cotisation_sante_emp = fields.Float(u'Cotisation Employé Santé (%)',
    #                                     digits_compute=Payroll)
    nif = fields.Char(u'NIF')
    ded_enfant_emp = fields.Float(u'Montant Allocation Familiale',
                                  digits_compute=Payroll)
    conge_mens = fields.Float(u'Nombre de jour congé mensuel',
                              digits_compute=Payroll)
    stat = fields.Char(u'STAT')
    organisme_ids = fields.One2many('res.organisme.medical', 'company_id',
                                    string=u'Organismes médicaux')
    use_parent_param = fields.Boolean(string=u"Utiliser les paramètres paie de la société parente",
                                      help=u'Cocher si vous voulez utiliser les paramètres de la société parente')
    additional_hours_authorized = fields.Boolean(string=u'Heures supplémentaires autorisées', default=True)
    hours_right = fields.Boolean(string=u'Droit heures nuit, dimanche et férié', default=True)
    monthly_hours_amount_id = fields.Many2one('monthly.hours.contract.data', string=u'Volume horaire mensuelle')  ##-
    automatic_compute_payslip_input = fields.Boolean('Calcul automatique des lignes de paie', default=False,
                                                     help=u'Si coché, le total aura la valeur du produit de la quantité et du montant dans la ligne de paie')
    trade_name = fields.Char(string=u"Nom commercial")
    status = fields.Selection(string=u"Statut", selection=[('status_1', 'Statut 1'), ('status_2', 'Statut 2'), ])
    compute_base_salary = fields.Selection([("yes", "OUI"), ("no", "NON")],
                                           string=u"Calcul automatique du salaire de base")
    legal_form = fields.Char(string=u"Forme juridique")
    logo_small = fields.Binary("Logo small")

    @api.model
    def get_new_size(self, data):
        image_stream = StringIO.StringIO(data.decode('base64'))
        image = Image.open(image_stream)
        img_width, img_height = image.size
        ratio = float(img_width) / float(img_height)
        if ratio >= 1:
            new_width = 225
            new_height = int(225 / ratio)
        else:
            new_height = 85
            new_width = int(85 * ratio)
        return tools.image_resize_image(data, (new_width, new_height))

    @api.model
    def create(self, vals):
        if vals.get('logo'):
            logo_small = self.get_new_size(vals.get('logo'))
            vals['logo_small'] = logo_small
        vals = super(ResCompany, self).create(vals)
        # Creation sequence
        self.sudo()._create_sequence(vals)

        return vals

    @api.multi
    def write(self, vals):
        if vals.get('logo'):
            logo_small = self.get_new_size(vals.get('logo'))
            vals['logo_small'] = logo_small
        res = super(ResCompany, self).write(vals)
        return res

    @api.model
    def _create_sequence(self, vals):
        """ Create new standard entry sequence for every new Company"""
        # Create sequence for CDI and Stagiaire type contract
        res = []
        seq_cdi = {
            'name': 'Sequence Matricule CDI(' + vals['name'] + ')',
            'code': self.slugify(vals['name'] + 'mat_cdi'),
            'implementation': 'standard',
            'prefix': None,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
            'company_id': vals['id'],
        }
        res.append(self.env['ir.sequence'].create(seq_cdi))
        seq_stg = {
            'name': 'Sequence Matricule Stagiaire(' + vals['name'] + ')',
            'code': self.slugify(vals['name'] + 'mat_stag'),
            'implementation': 'standard',
            'prefix': 'ST',
            'padding': 4,
            'number_increment': 1,
            'use_date_range': True,
            'company_id': vals['id'],
        }
        res.append(self.env['ir.sequence'].create(seq_stg))

        print res
        return res

    @api.model
    def slugify(self, str):
        slug = unicodedata.normalize("NFKD", unicode(str)).encode("ascii", "ignore")
        slug = re.sub(r"[^\w]+", " ", slug)
        slug = "_".join(slug.lower().strip().split())
        return slug

    """
    __________________________________________________________________________________________

    @Description : FUNCTION TO COMPUTE AUTOMATICALLY FIELDS IN CHILD VIEW
                   IF "use_parent_param" IS CHECKED
    @Author: Sylvain Michel R.
    @Begins on : 08/12/2016
    @Latest update on : 08/12/2016
    __________________________________________________________________________________________

    """

    @api.multi
    @api.onchange('use_parent_param')
    def onchange_use_parent_param(self):
        print self.use_parent_param
        if self.use_parent_param is True:
            self.seuil_irsa = self.parent_id.seuil_irsa
            self.taux_irsa = self.parent_id.taux_irsa
            self.abat_irsa = self.parent_id.abat_irsa
            self.cotisation_cnaps_patr = self.parent_id.cotisation_cnaps_patr
            self.cotisation_cnaps_emp = self.parent_id.cotisation_cnaps_emp
            self.plafond_cnaps = self.parent_id.plafond_cnaps
            self.seuil_irsa = self.parent_id.seuil_irsa
            self.ded_enfant_emp = self.parent_id.ded_enfant_emp
            self.conge_mens = self.parent_id.conge_mens
            self.organisme_ids = self.parent_id.organisme_ids
            self.monthly_hours_amount_id = self.parent_id.monthly_hours_amount_id
        else:
            # self.seuil_irsa = self.taux_irsa = self.abat_irsa = self.cotisation_cnaps_patr \
            # = self.cotisation_cnaps_emp = self.plafond_cnaps = self.seuil_irsa = self.ded_enfant_emp = self.conge_mens = 0.0

            if len(self.organisme_ids) > 0:
                # Delete all records
                self.organisme_ids = [(6, 0, [])]

    @api.onchange('trade_name')
    def set_capital_name(self):
        if self.trade_name:
            capital_name = str(self.trade_name).upper()
            self.trade_name = capital_name

    # @api.multi
    # def _get_address_data(self, field_names, arg):
    #     result = super(ResCompany, self)._get_address_data(field_names, arg)
    #     # result = super(ResCompany, self)._get_address_data(self._cr, self._uid, self.ids, field_names, arg)
    #     return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(ResCompany, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if view_type in ['tree', 'kanban']:
            for node in doc.xpath('//%s' % view_type):
                node.set('create', 'false')
                node.set('delete', 'false')
        if self.env.user.has_group('hr_copefrito_paie.group_direction'):
            if view_type == 'form':
                for node in doc.xpath('//form'):
                    node.set('edit', 'false')
        result['arch'] = etree.tostring(doc)
        return result
