from sqlite3 import Connection
from datetime import datetime
import common_utils
import re


def dump_to_text(con):
    date_str = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    with open(f"dump_{date_str}.txt", 'w') as f:

        tables = ("items", "box_inventory",
                  "warehouse_inventory", "box_transactions",
                  "warehouse_transactions, expiration_dates")
        for table in tables:
            f.write("-------------------------------------------------------\n")
            f.write(f"              {table.upper()}\n")
            f.write("-------------------------------------------------------\n\n")

            res = con.cursor().execute(f"select * from {table}")
            rows = res.fetchall()
            for row in rows:
                f.write(f"{'\t'.join([str(v) for v in row])}\n")

        f.write(show_inventory(con, "box", "bi sticker") + "\n\n")

        f.write(show_inventory(con, "box", "biq") + "\n\n")
        f.write(show_box_restock(con) + "\n\n")
        f.write(show_inventory(con, "warehouse", "wiq") + "\n\n")
        f.write(show_warehouse_restock(con) + "\n\n")


def totals(con, summarized=True, diapers_only=False):
    sql = ("select i.item_id, item_name, sum(quantity_changed) qsum "
           "from box_transactions b join items i on b.item_id = i.item_id"
           " where quantity_changed < 0 ")
    if diapers_only:
        sql += " and item_name like 'diaper%' "

    sql += "group by 1,2 having qsum < 0 order by qsum desc"

    res = con.cursor().execute(sql)

    if not res:
        print("No items were distributed")
        return

    # TODO put in some table
    items = {"diapers": {6, 7, 8, 9, 10, 11, 5},
             "formula": {2, 3, 4, 29},
             "toothpaste": {14, 31},
             "toothbrushes": {17, 18},
             "moisturizer": {35, 21},
             "soap": {20, 32},
             "pads": {1, 37},
             "baby wash/lotion": {25, 36, 24},
             "shampoo": {34, 28},
             "conditioner": {30, 33},
             "hairbrushes": {12, 13}}

    categories = {}
    for item in items:
        categories[item] = 0

    print("We distributed:\n")

    for row in res.fetchall():
        item_id, item_name, quantity = row
        found = False
        if summarized:
            for product_category, ids in items.items():
                if item_id in ids:
                    categories[product_category] += quantity
                    found = True
        if not found:
            categories[item_name] = quantity

    sorted_dict = dict(sorted(categories.items(), key=lambda x: x[1]))
    for item_name, quantity in sorted_dict.items():
        if quantity != 0:
            print(f"{abs(quantity)} {item_name}")


def show_box_restock(con: Connection):
    out = ["---------------------------------",
           "BOX OUT OF STOCK",
           "---------------------------------"]

    warehouse = {}

    sql = (f"select i.item_id, sum(quantity) as qsum from warehouse_inventory w "
           f"join items i  on w.item_id = i.item_id where hide=0 group by 1")

    res = con.cursor().execute(sql)
    rows = res.fetchall()
    for row in rows:
        item_id, quantity = row
        warehouse[item_id] = int(quantity)

    sql = (f"select i.item_id, item_name, sum(quantity) as qsum from box_inventory w "
           f"join items i  on w.item_id = i.item_id where hide=0 group by 1,2 having qsum = 0")

    res = con.cursor().execute(sql)
    rows = res.fetchall()

    for row in rows:
        item_id, name, quantity = row
        item_id = int(item_id)
        line = f"id {item_id} {name}"
        if item_id not in warehouse or warehouse[item_id] == 0:
            line += "\t** BUY **  "
        else:
            line += f"\twarehouse has: {warehouse[item_id]}"

        out.append(line)

    print("\n".join(out))
    return "\n".join(out)


def show_warehouse_restock(con: Connection):

    out = ["---------------------------------",
           "WAREHOUSE OUT OF STOCK",
           "---------------------------------"]

    sql = (f"select i.item_id, item_name, sum(quantity) as qsum from warehouse_inventory w "
           f"join items i  on w.item_id = i.item_id where hide=0 group by 1,2 having qsum = 0")

    res = con.cursor().execute(sql)
    rows = res.fetchall()

    if not rows:
        out.append(f"No items to restock in warehouse_inventory")

    for row in rows:
        item_id, name, quantity = row
        out.append(f"id {item_id} {name}, units: {quantity}")

    print("\n".join(out))
    return "\n".join(out)


def show_inventory(con: Connection, table_type, cmd=""):
    list_by_stickers = False
    ar = cmd.split(" ")
    if table_type == "box" and len(ar) == 2 and ar[1].startswith("sticker"):
        list_by_stickers = True

    item_to_search_for = ""
    if len(ar) == 2 and not re.search("[^0-9]", ar[1]):
        item_to_search_for = ar[1]
        if not common_utils.item_exists(con, item_to_search_for):
            return None

    # if the command was wiq or biq, order by quantity
    order_by_quantity = ar[0].endswith("q")

    out = ["---------------------------------",
           f"{table_type.upper()} INVENTORY",
           "---------------------------------"]

    if table_type == "box" and list_by_stickers:
        sql = f"select i.item_id, item_name, sticker, sum(quantity) from {table_type}_inventory w "

    else:
        sql = f"select i.item_id, item_name, 0 as sticker, sum(quantity) from {table_type}_inventory w "

    sql += f"join items i on w.item_id = i.item_id where quantity > 0 "
    if item_to_search_for:
        sql += f" and i.item_id = {item_to_search_for} "

    sql += " group by 1,2,3 "

    if order_by_quantity:
        sql += " order by 4, item_name"
    else:
        sql += " order by item_name"

    res = con.cursor().execute(sql)
    rows = res.fetchall()

    if not rows:
        if item_to_search_for:
            out.append(f"Item {item_to_search_for} is not in {table_type}_inventory")
        else:
            out.append(f"No items in {table_type}_inventory")

    for row in rows:
        item_id, name, sticker, quantity = row
        line = f"id {item_id} {name}, units: {quantity}"
        if sticker:
            line += f", sticker: {sticker}"

        out.append(line)

    print("\n".join(out))

    return "\n".join(out)


def show_transactions(con: Connection, table_type, cmd):
    limit = 1000
    ar = cmd.split(" ")
    if len(ar) == 2:
        limit = ar[1]

    if table_type == "box":
        sql = f"select i.item_id, item_name, quantity_changed, sticker, last_updated from {table_type}_transactions w "
    else:
        sql = (f"select i.item_id, item_name, quantity_changed, 0 as sticker, last_updated from "
               f"{table_type}_transactions w ")

    sql += f"join items i  on w.item_id = i.item_id order by last_updated desc limit {limit}"

    res = con.cursor().execute(sql)

    n = 0
    for n, row in enumerate(res.fetchall()):
        item_id, name, quantity, sticker, last_updated = row
        sticker_str = ""
        if sticker != 0:
            sticker_str = f"sticker: {sticker}"
        print(f"id {item_id} {name}: {quantity} {sticker_str} {common_utils.eastern_time(last_updated)}")

    print(n + 1, "rows")


def show_max_sticker(con):
    max_sticker = 0
    tables = ['box_inventory', 'expiration_dates']
    for table in tables:
        s = f"select max(sticker) from {table}"
        res = con.cursor().execute(s)
        row = res.fetchone()
        if row and row[0] and int(row[0]) > max_sticker:
            max_sticker = int(row[0])

    if max_sticker:
        print(f"Last sticker was {max_sticker}")
    else:
        print("No stickers")


def list_items(con: Connection, cmd):
    # can specify a search term to list
    ar = cmd.split(" ")

    sql = "select * from items"

    # list hidden means
    if len(ar) > 1:
        if ar[1] == "hidden":
            sql += " where hide=1 "
        else:
            sql += f" where item_name like '{ar[1]}%' and hide=0"

    else:
        sql += " where hide=0 "

    sql += " order by item_name"

    res = con.cursor().execute(sql)
    for row in res.fetchall():
        print(f"{row[0]}: {row[1]}")
