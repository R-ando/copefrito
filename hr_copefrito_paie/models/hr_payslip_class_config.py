# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.osv import expression
from lxml import etree
from openerp.exceptions import UserError

class HrPayslipClassConfig(models.Model):
    _name = 'hr.payslip.class.config'
    _order = 'code'
    
    name = fields.Char("Nom", required=True)
    # code = fields.Integer("Code", required=True)
    code = fields.Char("Code", required=True)
    category_id = fields.Many2one('hr.salary.rule.category', 'Categorie', required=True)

    @api.multi
    @api.depends('code', 'name')
    def name_get(self):
        result = []
        for class_conf in self:
            result.append((class_conf.id, str(class_conf.code) + " - " + class_conf.name))
        return result
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
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
                raise UserError(_('Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.') % (gb,))
 
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
 
        groupby_terms, orderby_terms = self._read_group_prepare(cr, uid, order, aggregated_fields, annotated_groupbys, query, context=context)
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
 
        data = map(lambda r: {k: self._read_group_prepare_data(k,v, groupby_dict, context) for k,v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, groupby_dict, domain, context) for d in data]
        if lazy and groupby_fields[0] in self._group_by_full:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way 
            result = self._read_group_fill_results(cr, uid, domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                                                       aggregated_fields, count_field, result, read_group_order=order,
                                                       context=context)
         
        return result
    
#    @api.model
#    def name_search(self, name, args=None, operator='ilike', limit=100):
#        args = args or []
#        domain = []
#        if name:
#            try:
#                intName = int(name)
#                domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
#            except ValueError:
#                domain = [('name', operator, name)]
#            #domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
#            if operator in expression.NEGATIVE_TERM_OPERATORS:
#                domain = ['&', '!'] + domain[1:]
#        class_conf = self.search(domain + args, limit=limit)
#        return class_conf.name_get()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(HrPayslipClassConfig, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if not self._context.get('from_many2one_link'):
            if self.env.user in self.env.ref('hr_copefrito_paie.group_system_admin').users:
                for node in doc.xpath("//form"):
                    node.set('edit', 'true')
                    if self.env.user == self.env.ref('base.user_root'):
                        node.set('create', 'true')
            if self.env.user == self.env.ref('base.user_root'):
                for node in doc.xpath("//tree"):
                    node.set('create', 'true')
            result['arch'] = etree.tostring(doc)
        return result

    @api.model
    def create(self, vals):
        if not vals.has_key('category_id'):
            categ_id = self.env['hr.salary.rule.category'].create({
                'name': vals['name'],
                'code': vals['name'].upper().replace(' ', '_')
            })
            vals['category_id'] = categ_id.id
        return super(HrPayslipClassConfig, self).create(vals)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator not in ('ilike', 'like', '=', '=like', '=ilike'):
            return super(HrPayslipClassConfig, self).name_search(name, args, operator, limit)
        args = args or []
        domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()