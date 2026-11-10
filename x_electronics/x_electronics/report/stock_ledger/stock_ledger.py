import frappe
from frappe import _
from frappe.utils import get_datetime, getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    validate_filters(filters)
    return get_columns(), get_data(filters)


def validate_filters(filters):
    if not filters.from_date or not filters.to_date:
        frappe.throw(_("From Date and To Date are required."))
    if getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw(_("From Date cannot be after To Date."))


def get_columns():
    return [
        {"label": _("Posting Datetime"), "fieldname": "posting_datetime", "fieldtype": "Datetime", "width": 160},
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 140},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Link", "options": "DocType", "width": 120},
        {"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 130},
        {"label": _("Qty Change"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 100},
        {"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("Valuation Rate"), "fieldname": "val_rate", "fieldtype": "Currency", "width": 110},
        {"label": _("Balance Value"), "fieldname": "bal_value", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    # Item and warehouse can be filtered inside the query. They are the window's
    # partition keys, so the running totals stay correct. The upper date limit is
    # safe too. The FROM date is applied outside, so earlier rows still count
    # towards the running balance but stay hidden.
    conditions = ["posting_datetime <= %(to_datetime)s"]
    values = {
        "from_datetime": get_datetime(f"{getdate(filters.from_date)} 00:00:00"),
        "to_datetime": get_datetime(f"{getdate(filters.to_date)} 23:59:59"),
    }
    if filters.get("item"):
        conditions.append("item = %(item)s")
        values["item"] = filters.item
    if filters.get("warehouse"):
        conditions.append("warehouse = %(warehouse)s")
        values["warehouse"] = filters.warehouse

    return frappe.db.sql(
        f"""
        SELECT t.*, t.bal_qty * t.val_rate AS bal_value
        FROM (
            SELECT
                name, item, warehouse, posting_datetime, actual_qty, incoming_rate,
                voucher_type, voucher_no,
                SUM(actual_qty) OVER w AS bal_qty,
                COALESCE(
                    SUM(CASE WHEN actual_qty > 0 THEN actual_qty * incoming_rate ELSE 0 END) OVER w
                    / NULLIF(SUM(CASE WHEN actual_qty > 0 THEN actual_qty ELSE 0 END) OVER w, 0),
                    0
                ) AS val_rate
            FROM `tabStock Ledger Entry`
            WHERE {" AND ".join(conditions)}
            WINDOW w AS (PARTITION BY item, warehouse ORDER BY posting_datetime, name)
        ) t
        WHERE t.posting_datetime >= %(from_datetime)s
        ORDER BY t.posting_datetime, t.name
        """,
        values,
        as_dict=True,
    )