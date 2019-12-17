# -*- coding: utf-8 -*-

from openerp import models, api


class HrTimesheetSheetSheetDay(models.Model):
    _inherit = 'hr_timesheet_sheet.sheet.day'

    def init(self, cr):
        print("\n=== in new sql")
        cr.execute("""create or replace view %s as
            SELECT
                id,
                name,
                sheet_id,
                total_timesheet,
                total_attendance,
                cast(round(cast(total_attendance - total_timesheet as Numeric),2) as Double Precision) AS total_difference
            FROM
                ((
                    SELECT
                        MAX(id) as id,
                        name,
                        sheet_id,
                        timezone,
                        SUM(total_timesheet) as total_timesheet,
                        CASE WHEN SUM(orphan_attendances) != 0
                            THEN (SUM(total_attendance) +
                                CASE WHEN current_date <> name
                                    THEN 1440
                                    ELSE (EXTRACT(hour FROM current_time AT TIME ZONE 'UTC' AT TIME ZONE coalesce(timezone, 'UTC')) * 60) + EXTRACT(minute FROM current_time AT TIME ZONE 'UTC' AT TIME ZONE coalesce(timezone, 'UTC'))
                                END
                                )
                            ELSE SUM(total_attendance)
                        END /60  as total_attendance
                    FROM
                        ((
                            select
                                min(l.id) as id,
                                p.tz as timezone,
                                l.date::date as name,
                                s.id as sheet_id,
                                sum(l.unit_amount) as total_timesheet,
                                0 as orphan_attendances,
                                0.0 as total_attendance
                            from
                                account_analytic_line l
                                LEFT JOIN hr_timesheet_sheet_sheet s ON s.id = l.sheet_id
                                JOIN hr_employee e ON s.employee_id = e.id
                                JOIN resource_resource r ON e.resource_id = r.id
                                LEFT JOIN res_users u ON r.user_id = u.id
                                LEFT JOIN res_partner p ON u.partner_id = p.id
                            group by l.date::date, s.id, timezone
                        ) union (
                            select
                                -min(a.id) as id,
                                p.tz as timezone,
                                (a.parent_name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date as name,
                                s.id as sheet_id,
                                0.0 as total_timesheet,
                                0 as orphan_attendances,
                                abs(SUM((EXTRACT(hour FROM (a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))) * 60 + EXTRACT(minute FROM (a.name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))))
                                - (EXTRACT(hour FROM (a.parent_name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))) * 60 + EXTRACT(minute FROM (a.parent_name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC')))))) as total_attendance
                            from
                                hr_attendance a
                                LEFT JOIN hr_timesheet_sheet_sheet s
                                ON s.id = a.sheet_id
                                JOIN hr_employee e
                                ON a.employee_id = e.id
                                JOIN resource_resource r
                                ON e.resource_id = r.id
                                LEFT JOIN res_users u
                                ON r.user_id = u.id
                                LEFT JOIN res_partner p
                                ON u.partner_id = p.id
                            WHERE parent_name IS NOT NULL
                            group by (a.parent_name AT TIME ZONE 'UTC' AT TIME ZONE coalesce(p.tz, 'UTC'))::date, s.id, timezone
                        )) AS foo
                        GROUP BY name, sheet_id, timezone
                )) AS bar""" % self._table)
