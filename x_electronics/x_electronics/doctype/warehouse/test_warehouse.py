# Copyright (c) 2026, Faisal and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from x_electronics.doctype.stock_entry.test_stock_entry import make_item, make_stock_entry, make_test_warehouses

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestWarehouse(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        make_test_warehouses()

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    def test_parent_must_be_a_group(self):
        doc = frappe.get_doc(
            {"doctype": "Warehouse", "warehouse_name": "Test Bad Child", "parent_warehouse": "Test Store A"}
        )
        with self.assertRaises(frappe.ValidationError):
            doc.insert()

    def test_warehouse_with_stock_cannot_become_a_group(self):
        item = make_item("TEST-WH-ITEM")
        make_stock_entry("Receipt", item.name, 5, 100, target="Test Store A")

        store = frappe.get_doc("Warehouse", "Test Store A")
        store.is_group = 1
        with self.assertRaises(frappe.ValidationError):
            store.save()