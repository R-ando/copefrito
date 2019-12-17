from openerp import SUPERUSER_ID
from openerp.osv import fields, osv

class res_company_osv_inherit(osv.osv):
    _inherit = "res.company"

    _defaults = {
        'country_id': lambda s, cr, uid, c: s.pool.get('ir.model.data').xmlid_to_object(cr, SUPERUSER_ID, 'base.mg')
    }