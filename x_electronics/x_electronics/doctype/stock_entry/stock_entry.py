# Copyright (c) 2026, Faisal and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime, get_time, getdate

from x_electronics.stock_utils import get_valuation_rate


class StockEntry(Document):
    def validate(self):
        self.validate_warehouses()
        self.validate_items()

    def validate_warehouses(self):
        needs_source = self.stock_entry_type in ("Consume", "Transfer")
        needs_target = self.stock_entry_type in ("Receipt", "Transfer")

        if needs_source and not self.source_warehouse:
            frappe.throw(_("Source Warehouse is required for a {0}.").format(self.stock_entry_type))
        if needs_target and not self.target_warehouse:
            frappe.throw(_("Target Warehouse is required for a {0}.").format(self.stock_entry_type))

        if not needs_source:
            self.source_warehouse = None
        if not needs_target:
            self.target_warehouse = None

        if self.source_warehouse and self.source_warehouse == self.target_warehouse:
            frappe.throw(_("Source and Target Warehouse cannot be the same."))

        for warehouse in (self.source_warehouse, self.target_warehouse):
            if warehouse and frappe.db.get_value("Warehouse", warehouse, "is_group"):
                frappe.throw(_("{0} is a group warehouse. Choose a non-group warehouse.").format(warehouse))

    def validate_items(self):
        if not self.items:
            frappe.throw(_("Add at least one item."))

        for row in self.items:
            if flt(row.qty) <= 0:
                frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx))

            if frappe.db.get_value("Item", row.item, "disabled"):
                frappe.throw(_("Row {0}: Item {1} is disabled.").format(row.idx, row.item))

            if self.stock_entry_type == "Receipt":
                if flt(row.basic_rate) < 0:
                    frappe.throw(_("Row {0}: Basic Rate cannot be negative.").format(row.idx))
            else:
                # Outgoing stock is valued by the moving average, never typed in
                row.basic_rate = 0

    # ---- posting ----

    def on_submit(self):
        self.make_ledger_entries()

    def on_cancel(self):
        frappe.db.delete(
            "Stock Ledger Entry",
            {"voucher_type": self.doctype, "voucher_no": self.name},
        )

    def get_posting_datetime(self):
        return get_datetime(f"{getdate(self.posting_date)} {get_time(self.posting_time)}")

    def make_ledger_entries(self):
        posting_datetime = self.get_posting_datetime()

        for row in self.items:
            qty = flt(row.qty)

            if self.stock_entry_type == "Receipt":
                self.make_entry(row, self.target_warehouse, qty, flt(row.basic_rate), posting_datetime)

            elif self.stock_entry_type == "Consume":
                self.make_entry(row, self.source_warehouse, -qty, 0, posting_datetime)

            else:
                # Transfer: the incoming side takes the source's moving average rate
                rate = get_valuation_rate(row.item, self.source_warehouse, posting_datetime)
                self.make_entry(row, self.source_warehouse, -qty, 0, posting_datetime)
                self.make_entry(row, self.target_warehouse, qty, rate, posting_datetime)

    def make_entry(self, row, warehouse, actual_qty, incoming_rate, posting_datetime):
        frappe.get_doc(
            {
                "doctype": "Stock Ledger Entry",
                "item": row.item,
                "warehouse": warehouse,
                "posting_datetime": posting_datetime,
                "actual_qty": actual_qty,
                "incoming_rate": incoming_rate,
                "voucher_type": self.doctype,
                "voucher_no": self.name,
                "voucher_detail_no": row.name,
            }
        ).insert(ignore_permissions=True)
