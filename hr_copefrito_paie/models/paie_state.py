# -*- coding: utf-8 -*-

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import models, api, fields
from openerp.netsvc import logging
_logger = logging.getLogger(__name__)

from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError

import datetime
import time
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)
    
class pay_recap(models.Model):    
    _name = "pay.recap"
    _description = "Dirickx Paie Recap."
    _auto = False

    id = fields.Integer(u'id')
    pay_number = fields.Char(u'Référence bulletin')
    name = fields.Char(u'Nom employé')

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'pay_recap')
        cr.execute("""

				    create or replace function colpivot(
				    out_table varchar, in_query varchar,
				    key_cols varchar[], class_cols varchar[],
				    value_e varchar, col_order varchar
				) returns void as $$
				    declare
				        in_table varchar;
				        col varchar;
				        ali varchar;
				        on_e varchar;
				        i integer;
				        rec record;
				        query varchar;
				        
				        clsc_cols text[] := array[]::text[];
				        n_clsc_cols integer;
				        n_class_cols integer;
				    begin
				        in_table := quote_ident('__' || out_table || '_in');
				        execute ('create temp table ' || in_table || ' on commit drop as ' || in_query);
				        -- get ordered unique columns (column combinations)
				        query := 'select array[';
				        i := 0;
				        foreach col in array class_cols loop
				            if i > 0 then
				                query := query || ', ';
				            end if;
				            query := query || 'quote_literal(' || quote_ident(col) || ')';
				            i := i + 1;
				        end loop;
				        
				        query := query || '] x from ' || in_table;
				        for j in 1..2 loop
				            if j = 1 then
				                query := query || ' group by ';
				            else
				                query := query || ' order by ';
				                if col_order is not null then
				                    query := query || col_order || ' ';
				                    exit;
				                end if;
				            end if;
				            i := 0;
				            foreach col in array class_cols loop
				                if i > 0 then
				                    query := query || ', ';
				                end if;
				                query := query || quote_ident(col);
				                i := i + 1;
				            end loop;
				        end loop;
				        
				        -- raise notice '%', query;
				        for rec in
				            execute query
				        loop
				            clsc_cols := array_cat(clsc_cols, rec.x);
				        end loop;
				        n_class_cols := array_length(class_cols, 1);
				        n_clsc_cols := array_length(clsc_cols, 1) / n_class_cols;
				        -- build target query
				        query := 'select ';
				        i := 0;
				        foreach col in array key_cols loop
				            if i > 0 then
				                query := query || ', ';
				            end if;
				            query := query || '_key.' || quote_ident(col) || ' ';
				            i := i + 1;
				        end loop;
				        for j in 1..n_clsc_cols loop
				            query := query || ', ';
				            col := '';
				            for k in 1..n_class_cols loop
				                if k > 1 then
				                    col := col || ', ';
				                end if;
				                col := col || clsc_cols[(j - 1) * n_class_cols + k];
				            end loop;
				            raise notice 'Value 11 : %', col;
				            ali := '_clsc_' || j::text;
				            query := query || 'coalesce((' || replace(value_e, '#', ali) || '),0)' || ' as ' || quote_ident(col) || ' ';
				        end loop;
				        query := query || ' from (select distinct ';
				        i := 0;
				        foreach col in array key_cols loop
				            if i > 0 then
				                query := query || ', ';
				            end if;
				            query := query || quote_ident(col) || ' ';
				            i := i + 1;
				        end loop;
				        raise notice 'Value 2 : %', replace(query,'''','');
				        query := replace(query,'''','');
				        query := query || ' from ' || in_table || ') _key ';
				        for j in 1..n_clsc_cols loop
				            ali := '_clsc_' || j::text;
				            on_e := '';
				            i := 0;
				            foreach col in array key_cols loop
				                if i > 0 then
				                    on_e := on_e || ' and ';
				                end if;
				                on_e := on_e || ali || '.' || quote_ident(col) || ' = _key.' || quote_ident(col) || ' ';
				                i := i + 1;
				            end loop;
				            for k in 1..n_class_cols loop
				                on_e := on_e || ' and ';
				                on_e := on_e || ali || '.' || quote_ident(class_cols[k]) || ' = ' || clsc_cols[(j - 1) * n_class_cols + k];
				            end loop;
				            query := query || 'left join ' || in_table || ' as ' || ali || ' on ' || on_e || ' ';
				        end loop;
				        -- raise notice '%', query;
				        execute ('create temp table ' || quote_ident(out_table) || ' on commit drop as ' || query);
				        -- cleanup temporary in_table before we return
				        execute ('drop table ' || in_table)
				        return;
				    end;
				$$ language plpgsql volatile;

				select colpivot('pivoted', 'select * from hr_payslip_line',
				array['slip_id'], array['code'], '#.total', null);

				CREATE or REPLACE view x AS    
				select pay.id  as id,pay.number,employee.name_related,"master".* from pivoted as master
				inner join hr_payslip as pay on pay.id = master.slip_id
				left join hr_employee as employee on (pay.employee_id = employee.id)	
				order by slip_id;

				DROP table if exists temp_table CASCADE;

				CREATE TABLE temp_table AS 
				select pay.id as id,pay.number as pay_number,employee.name_related as name,"master".* from pivoted as master
				inner join hr_payslip as pay on pay.id = master.slip_id
				left join hr_employee as employee on (pay.employee_id = employee.id)	
				order by slip_id;


				create or replace view pay_recap as select * from temp_table




					"""
					)