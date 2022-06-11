import frappe, json
from six import string_types

@frappe.whitelist()
def get_jobcard_planning_details(start, end, filters=None):

    events = []

    event_color = {
        "Material Transferred": "blue",
        "Work In Progress": "orange",
    }

    from frappe.desk.reportview import get_filters_cond

    conditions = get_filters_cond("Job Card", filters, [])

    job_cards = frappe.db.sql(
        """  SELECT `tabJob Card`.name, `tabJob Card`.work_order,
            `tabJob Card`.status, ifnull(`tabJob Card`.remarks, ''),
            `tabJob Card`.operation,
            `tabCustomer`.customer_name,
            tabItem.item_name,
            `tabJob Card`.planned_start_date,
            `tabJob Card`.planned_end_date,
            `tabJob Card`.planned_employee_name,
            min(`tabJob Card Time Log`.from_time) as initial_start_date,
            max(`tabJob Card Time Log`.from_time) as initial_end_date
        FROM `tabJob Card` INNER JOIN `tabJob Card Time Log`
        ON `tabJob Card`.name = `tabJob Card Time Log`.parent
        INNER JOIN `tabWork Order` ON `tabWork Order`.name=`tabJob Card`.work_order
        INNER JOIN `tabItem` ON `tabItem`.item_name=`tabWork Order`.item_name
        LEFT JOIN `tabSales Order` ON `tabSales Order`.name=`tabWork Order`.sales_order
        LEFT JOIN `tabCustomer` ON `tabCustomer`.name=`tabSales Order`.customer
        WHERE
             `tabJob Card`.status<>'Completed'
             {0}
            group by `tabJob Card`.name""".format(
            conditions
        ),
        as_dict=1,
    )

    # Attemp to make it with query Builder, but there is no
    # to convert form filters to .where()

    # from frappe.query_builder.functions import Min, Max
    # JobCard = frappe.qb.DocType("Job Card")
    # JobCardTimeLog = frappe.qb.DocType("Job Card Time Log")
    # job_cards_query = (
    #     frappe.qb.from_(JobCard)
    #     .inner_join(JobCardTimeLog)
    #     .on(JobCard.name == JobCardTimeLog.parent)
    #     .groupby(JobCard.name)
    #     .having(Min(JobCardTimeLog.from_time) >= start)
    #     .having(Max(JobCardTimeLog.from_time) <= end)
    #     .select(
    #         JobCard.name,
    #         JobCard.work_order,
    #         JobCard.status,
    #         JobCard.remarks,
    #         JobCard.planned_start_date,
    #         JobCard.planned_end_date,
    #         Min(JobCardTimeLog.from_time).as_('initial_start_date'),
    #     )
    # )
    #job_cards = job_cards_query.run(as_dict=1)

    for d in job_cards:
        subject_data = []
        for field in ["customer_name", "item_name", "operation", "planned_employee_name", "work_order"]:
            if not d.get(field):
                continue

            subject_data.append(d.get(field))

        if (d.planned_start_date is None):
            color = '#D3D3D3'
            start_date = d.initial_start_date
            end_date = d.initial_end_date
        else:
            color = event_color.get(d.status)
            start_date = d.planned_start_date
            end_date = d.planned_start_end

        job_card_data = {
            "planned_start_date": start_date,
            "planned_end_date": end_date,
            "name": d.name,
            "subject": "\n".join(subject_data),
            "color": color if color else "#89bcde",
        }

        events.append(job_card_data)

    return events

@frappe.whitelist()
def update_jobcard_planned_date(args, field_map):
    """Updates Event (called via calendar) based on passed `field_map`"""
    args = frappe._dict(json.loads(args))
    field_map = frappe._dict(json.loads(field_map))
    w = frappe.get_doc(args.doctype, args.name)
    w.set(field_map.start, args[field_map.start])
    w.set(field_map.end, args.get(field_map.end))
    w.save()
