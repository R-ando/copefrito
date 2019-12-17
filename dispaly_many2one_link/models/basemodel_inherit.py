# -*- coding: utf-8 -*-

import openerp
from openerp.models import BaseModel
from lxml import etree
from openerp.osv.orm import setup_modifiers

fields_view_get_original = BaseModel.fields_view_get


@openerp.api.model
def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    context = self._context
    result = fields_view_get_original(self, view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

    def del_key(dic, key):
        try:
            del dic[key]
        except KeyError:
            pass

    if context.get('from_many2one_link') and view_type == 'form':
        doc = etree.XML(result['arch'])
        for node in doc.xpath("//form"):
            node.set('edit', 'false')
            node.set('create', 'false')
            node.set('delete', 'false')
        for node in doc.xpath("//header//button"):
            # should delete the key state because it raise a bug in "def transfer_field_to_modifiers(field, modifiers):"
            # in openerp/osv/orm.py line: 38
            if 'states' in node.attrib:
                del (node.attrib['states'])
            node.set('invisible', '1')
            # node.set('invisible', '1') is not applied even if we don't call set_up_modifiers
            setup_modifiers(node, node.attrib)
        del_key(result, 'toolbar')
        result['arch'] = etree.tostring(doc)
    return result


BaseModel.fields_view_get = fields_view_get
