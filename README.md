# X Electronics: Warehouse Management

A small stock system built on Frappe for X Electronics. Items can be kept, warehouses are set up as a tree, stock moves in, out and between warehouses, and the reports show where everything is and what's their worth.

- **Item**: the products. The item code is its name.
- **Warehouse**: a tree. A group warehouse (like "Mumbai Hub") holds other warehouses. Stock only lives in the ones that aren't groups.
- **Stock Entry**: how stock moves. Three types:
  - **Receipt**: stock comes in to a warehouse, at the rate typed in the entry.
  - **Consume**: stock goes out of a warehouse.
  - **Transfer**: stock moves from one warehouse to another.
- **Stock Ledger Entry**: one row for every movement. Nobody creates these by hand, and nobody can edit them.
- **Reports**: Stock Ledger and Stock Balance.

## Install

Needs a working [bench](https://github.com/frappe/bench) with a site.

```sh
cd ~/frappe-bench
bench get-app https://github.com/unofaisal/xelectronics.git
bench --site <your-site> install-app x_electronics
```

## Reports

- **Stock Ledger**: every movement with the running quantity, rate and value after it. Setting a From Date hides the earlier rows, but the balance still counts them.
- **Stock Balance**: the balance of each item on a date. Group warehouses add up everything under them, so "All Warehouses" shows the grand total. It can be filtered by item or warehouse, and zero stock can be hidden.