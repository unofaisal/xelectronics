# Copyright (c) 2026, Faisal and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class StockLedgerEntry(Document):
    def validate(self):
        # Ledger rows are append-only
        if not self.is_new():
            frappe.throw(_("Stock Ledger Entries cannot be modified."))

        self.validate_qty()
        self.validate_warehouse()
        self.validate_item()

    def validate_qty(self):
        if not self.actual_qty:
            frappe.throw(_("Actual Qty cannot be zero."))
        if (self.incoming_rate or 0) < 0:
            frappe.throw(_("Incoming Rate cannot be negative."))

    def validate_warehouse(self):
        if frappe.db.get_value("Warehouse", self.warehouse, "is_group"):
            frappe.throw(_("Stock can only be booked on non-group warehouses. {0} is a group.").format(self.warehouse))

    def validate_item(self):
        if frappe.db.get_value("Item", self.item, "disabled"):
            frappe.throw(_("Item {0} is disabled.").format(self.item))