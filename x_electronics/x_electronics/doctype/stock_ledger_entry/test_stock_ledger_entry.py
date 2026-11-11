# Copyright (c) 2026, Faisal and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from x_electronics.x_electronics.doctype.stock_entry.test_stock_entry import get_ledger, make_item, make_stock_entry, make_test_warehouses

EXTRA_TEST_RECORD_DEPENDENCIES = []
# voucher_type links to DocType. Loading test records for it would pull in core records we don't need.
IGNORE_TEST_RECORD_DEPENDENCIES = ["DocType"]


class IntegrationTestStockLedgerEntry(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        make_test_warehouses()

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    def test_ledger_rows_cannot_be_edited(self):
        # The ledger is append-only: balances are derived from it, so a row must never change.
        item = make_item("TEST-SLE-ITEM")
        make_stock_entry("Receipt", item.name, 10, 500, target="Test Store A")

        row = frappe.get_doc("Stock Ledger Entry", get_ledger(item.name)[0].name)
        row.actual_qty = 99
        with self.assertRaises(frappe.ValidationError):
            row.save()