# Copyright (c) 2026, Faisal and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Warehouse(NestedSet):
    nsm_parent_field = "parent_warehouse"

    def validate(self):
        self.validate_parent()
        self.validate_group_change()

    def validate_parent(self):
        if not self.parent_warehouse:
            return
        if not frappe.db.get_value("Warehouse", self.parent_warehouse, "is_group"):
            frappe.throw(_("Parent warehouse {0} must be a group.").format(self.parent_warehouse))

    def validate_group_change(self):
        if self.is_new():
            return

        if not self.is_group and frappe.db.exists("Warehouse", {"parent_warehouse": self.name}):
            frappe.throw(_("{0} has child warehouses, so it must stay a group.").format(self.name))

        if self.is_group and frappe.db.exists("Stock Ledger Entry", {"warehouse": self.name}):
            frappe.throw(_("{0} has stock ledger entries, so it cannot become a group.").format(self.name))

    def on_trash(self):
        super().on_trash(allow_root_deletion=True)
