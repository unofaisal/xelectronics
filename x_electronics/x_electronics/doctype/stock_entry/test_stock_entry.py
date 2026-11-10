# Copyright (c) 2026, Faisal and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []

A = "Test Store A"
B = "Test Store B"


class IntegrationTestStockEntry(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        make_test_warehouses()
        self.item = make_item("TEST-LAPTOP").name

    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    # ---- validation: the rules that protect the ledger ----

    def test_each_type_needs_its_warehouses(self):
        # Receipt needs a target, Consume needs a source, Transfer needs both (target missing here)
        cases = [("Receipt", {}), ("Consume", {}), ("Transfer", {"source": A})]
        for entry_type, warehouses in cases:
            with self.subTest(entry_type=entry_type), self.assertRaises(frappe.ValidationError):
                make_stock_entry(entry_type, self.item, 5, 100, submit=False, **warehouses)

    def test_stock_cannot_be_booked_on_a_group_warehouse(self):
        with self.assertRaises(frappe.ValidationError):
            make_stock_entry("Receipt", self.item, 5, 100, target="Test All", submit=False)

    def test_qty_must_be_positive(self):
        # A negative receipt would act as an issue and bypass the stock check
        with self.assertRaises(frappe.ValidationError):
            make_stock_entry("Receipt", self.item, -5, 100, target=A, submit=False)

    # ---- posting ----

    def test_receipt_posts_one_incoming_row(self):
        entry = make_stock_entry("Receipt", self.item, 10, 500, target=A)
        rows = get_ledger(self.item)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].warehouse, rows[0].actual_qty, rows[0].incoming_rate), (A, 10, 500))
        self.assertEqual(rows[0].voucher_no, entry.name)

    def test_consume_posts_one_outgoing_row(self):
        make_stock_entry("Receipt", self.item, 10, 500, target=A)
        make_stock_entry("Consume", self.item, 4, source=A, date="2026-01-02")
        self.assertEqual(get_ledger(self.item)[-1].actual_qty, -4)

    def test_transfer_posts_two_rows_priced_at_the_source_average(self):
        make_stock_entry("Receipt", self.item, 10, 500, target=A, date="2026-01-01")
        make_stock_entry("Receipt", self.item, 10, 600, target=A, date="2026-01-02")  # average is now 550
        make_stock_entry("Transfer", self.item, 5, source=A, target=B, date="2026-01-03")

        self.assertEqual(get_ledger(self.item, A)[-1].actual_qty, -5)
        incoming = get_ledger(self.item, B)[0]
        self.assertEqual(incoming.actual_qty, 5)
        self.assertAlmostEqual(incoming.incoming_rate, 550)

    def test_cancel_removes_the_ledger_rows(self):
        entry = make_stock_entry("Receipt", self.item, 10, 500, target=A)
        entry.cancel()
        self.assertEqual(get_ledger(self.item), [])

    # ---- negative stock ----

    def test_cannot_consume_more_than_is_in_stock(self):
        make_stock_entry("Receipt", self.item, 10, 500, target=A)
        entry = make_stock_entry("Consume", self.item, 11, source=A, date="2026-01-02", submit=False)

        # In a web request Frappe rolls back a failed submit. A test has to do that by hand.
        frappe.db.savepoint("before_submit")
        with self.assertRaises(frappe.ValidationError):
            entry.submit()
        frappe.db.rollback(save_point="before_submit")

        self.assertEqual(len(get_ledger(self.item)), 1)  # nothing from the failed entry is left

    def test_cannot_cancel_a_receipt_that_later_issues_depend_on(self):
        receipt = make_stock_entry("Receipt", self.item, 10, 500, target=A, date="2026-01-01")
        make_stock_entry("Consume", self.item, 6, source=A, date="2026-01-02")

        frappe.db.savepoint("before_cancel")
        with self.assertRaises(frappe.ValidationError):
            receipt.cancel()
        frappe.db.rollback(save_point="before_cancel")

        self.assertEqual(len(get_ledger(self.item)), 2)  # both rows are still there


# ---- helpers for the tests ----

def make_item(item_code, disabled=0):
    if frappe.db.exists("Item", item_code):
        return frappe.get_doc("Item", item_code)
    return frappe.get_doc(
        {"doctype": "Item", "item_code": item_code, "item_name": item_code, "disabled": disabled}
    ).insert()


def make_warehouse(name, parent=None, is_group=0):
    if frappe.db.exists("Warehouse", name):
        return frappe.get_doc("Warehouse", name)
    return frappe.get_doc(
        {"doctype": "Warehouse", "warehouse_name": name, "is_group": is_group, "parent_warehouse": parent}
    ).insert()


def make_test_warehouses():
    """Test All (group)
         |- Test Hub (group)
         |    |- Test Store A
         |- Test Store B
    """
    make_warehouse("Test All", is_group=1)
    make_warehouse("Test Hub", parent="Test All", is_group=1)
    make_warehouse("Test Store A", parent="Test Hub")
    make_warehouse("Test Store B", parent="Test All")


def make_stock_entry(entry_type, item, qty, rate=0, source=None, target=None,
                     date="2026-01-01", time="10:00:00", submit=True):
    entry = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "stock_entry_type": entry_type,
            "posting_date": date,
            "posting_time": time,
            "source_warehouse": source,
            "target_warehouse": target,
            "items": [{"item": item, "qty": qty, "basic_rate": rate}],
        }
    )
    entry.insert()
    if submit:
        entry.submit()
    return entry


def get_ledger(item, warehouse=None):
    filters = {"item": item}
    if warehouse:
        filters["warehouse"] = warehouse
    return frappe.get_all(
        "Stock Ledger Entry",
        filters=filters,
        fields=["name", "warehouse", "actual_qty", "incoming_rate", "voucher_no"],
        order_by="posting_datetime asc, name asc",
    )