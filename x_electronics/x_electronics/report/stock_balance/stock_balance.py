# Copyright (c) 2026, Faisal and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.as_on_date:
        frappe.throw(_("As On Date is required."))
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
        {"label": _("Group"), "fieldname": "is_group", "fieldtype": "Check", "width": 70},
        {"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 110},
        {"label": _("Valuation Rate"), "fieldname": "val_rate", "fieldtype": "Currency", "width": 120},
        {"label": _("Balance Value"), "fieldname": "bal_value", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    as_on = get_datetime(f"{getdate(filters.as_on_date)} 23:59:59")

    # Tree order: parents come before their children
    warehouses = frappe.get_all(
        "Warehouse", fields=["name", "is_group", "lft", "rgt"], order_by="lft asc"
    )
    position = {w.name: w for w in warehouses}

    query_filters = {"posting_datetime": ["<=", as_on]}
    if filters.get("item"):
        query_filters["item"] = filters.item

    rows = frappe.get_all(
        "Stock Ledger Entry",
        filters=query_filters,
        fields=["item", "warehouse", "actual_qty", "incoming_rate"],
    )

    # 1. Balance of each item in each leaf warehouse
    leaf = {}
    for row in rows:
        b = leaf.setdefault((row.item, row.warehouse), frappe._dict(qty=0, received_qty=0, received_value=0))
        b.qty += flt(row.actual_qty)
        if flt(row.actual_qty) > 0:
            b.received_qty += flt(row.actual_qty)
            b.received_value += flt(row.actual_qty) * flt(row.incoming_rate)

    # 2. Add each leaf's qty and value to itself and to every ancestor
    totals = {}
    for (item, warehouse), b in leaf.items():
        leaf_wh = position.get(warehouse)
        if not leaf_wh:
            continue

        rate = b.received_value / b.received_qty if b.received_qty else 0
        for w in warehouses:
            if w.lft <= leaf_wh.lft and leaf_wh.rgt <= w.rgt:  # w is the leaf itself or an ancestor
                t = totals.setdefault((item, w.name), frappe._dict(qty=0, value=0))
                t.qty += b.qty
                t.value += b.qty * rate

    # 3. Build the rows, in item then tree order
    selected = position.get(filters.warehouse) if filters.get("warehouse") else None

    data = []
    for item in sorted({key[0] for key in totals}):
        for w in warehouses:
            t = totals.get((item, w.name))
            if not t:
                continue
            # A chosen warehouse shows itself and everything beneath it
            if selected and not (selected.lft <= w.lft and w.rgt <= selected.rgt):
                continue
            if filters.get("hide_zero_stock") and not t.qty:
                continue

            data.append(
                {
                    "item": item,
                    "warehouse": w.name,
                    "is_group": w.is_group,
                    "bal_qty": t.qty,
                    "val_rate": t.value / t.qty if t.qty else 0,
                    "bal_value": t.value,
                }
            )

    return data
