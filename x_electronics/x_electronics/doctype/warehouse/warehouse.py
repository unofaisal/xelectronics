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
        # A warehouse with children has to stay a group
        if self.is_new() or self.is_group:
            return
        if frappe.db.exists("Warehouse", {"parent_warehouse": self.name}):
            frappe.throw(_("{0} has child warehouses, so it must stay a group.").format(self.name))

    def on_trash(self):
        # Allow deleting top-level warehouses too (Frappe blocks root deletion by default)
        super().on_trash(allow_root_deletion=True)
