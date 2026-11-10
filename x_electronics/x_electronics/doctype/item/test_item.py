# Copyright (c) 2026, Faisal and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestItem(IntegrationTestCase):
	"""
	Integration tests for Item.
	Use this class for testing interactions between multiple components.
	"""

	pass


import frappe
from frappe.tests import IntegrationTestCase


class TestItem(IntegrationTestCase):
    def tearDown(self):
        frappe.db.rollback()
        super().tearDown()

    def make(self, code="TEST-ITEM", **extra):
        return frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": "Test", **extra})

    def test_item_code_is_the_name(self):
        item = self.make("TEST-NAME-1").insert()
        self.assertEqual(item.name, "TEST-NAME-1")

    def test_defaults(self):
        item = self.make("TEST-DEFAULTS").insert()
        self.assertEqual(item.uom, "Nos")
        self.assertEqual(item.disabled, 0)

    def test_duplicate_item_code_is_rejected(self):
        self.make("TEST-DUP").insert()
        with self.assertRaises(frappe.DuplicateEntryError):
            self.make("TEST-DUP").insert()
