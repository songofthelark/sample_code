import sqlite3
import re
from sqlite3 import Connection
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse


def eastern_time(str_date):

    dateformat = "%Y-%m-%d %H:%M:%S"
    naive_dt = datetime.strptime(str_date, dateformat)
    utc_dt = naive_dt.replace(tzinfo=ZoneInfo("UTC"))
    eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))

    return eastern_dt.strftime(dateformat)

def error(msg):
    print("FAILED", msg)

def item_exists(con: Connection, item_id) -> bool:

    res = con.cursor().execute(f"select count(*) from items where item_id = {item_id}")
    count = res.fetchone()[0]

    if not count:
        error(f"No item id {item_id}")

    return count > 0


def item_needs_sticker(con, item_id):
    res = con.cursor().execute(f"select needs_sticker from items where item_id = {item_id}")
    needs_sticker  = res.fetchone()[0]

    return needs_sticker


def clear_all_tables(con):

    confirm = input("Type YES all caps if you mean it: ")
    if confirm.strip() != "YES":
        print("nevermind then")
        return

    cur = con.cursor()
    for table_type in ("warehouse", "box"):
        cur.execute(f"delete from {table_type}_inventory")
        cur.execute(f"delete from {table_type}_transactions")

    print("done")


def list_items(con: Connection, cmd):

    # can specify a search term to list
    ar = cmd.split(" ")

    sql = "select * from items"
    if len(ar) > 1:
        sql += f" where item_name like '{ar[1]}%'"

    sql += " order by item_name"

    res = con.cursor().execute(sql)
    for row in res.fetchall():
        print(f"{row[0]}: {row[1]}")


def recalculate_inventory(con:Connection, table_type, item_id:int, quantity_changed:int, sticker:int =0):

    # clunky sql placeholders for the extra parameter we need for box
    sph1 = sph2 = sph3 = ""
    if table_type == "box":
        sph1 = ", sticker"
        sph2 = f", {sticker}"
        sph3 = f" and sticker = {sticker}"

    cur = con.cursor()

    res = cur.execute(f"select * from {table_type}_inventory where item_id = {item_id} {sph3}")
    row = res.fetchone()
    if not row:

        # nothing in there with the item id, so add it, IF is a positive number
        if int(quantity_changed) < 0:
            error(f"Sticker or item not found, so quantity can't be negative")
            return False

        cur.execute(f"insert into {table_type}_inventory (item_id, quantity {sph1})"
                    f" values ({item_id}, {quantity_changed} {sph2}) ")
    else:

        cur.execute((f"update {table_type}_inventory set quantity=quantity+{quantity_changed} "
                    f"where item_id = {item_id} {sph3}"))

    con.commit()
    return True


def get_item_quantity(con, table_type, item_id):
    s = (f"select i.item_id, item_name, sum(quantity) from {table_type}_inventory x "
         f"join items i on i.item_id = x.item_id where i.item_id={item_id} group by i.item_id, item_name")

    res = con.cursor().execute(s)
    row = res.fetchone()
    if row:
        return row[0], row[1], row[2]
    return  0, "(none)", 0


def warehouse_transaction(con:Connection, cmd):

    item_id, quantity_changed, sticker = check_cmd_line(cmd)
    if item_id <= 0:
        error("Bad command, should be wadd i# q#")
        return

    if not item_exists(con, item_id):
        return

    _, name, box_quantity = get_item_quantity(con, "box", item_id)
    _, _, warehouse_quantity = get_item_quantity(con, "warehouse", item_id)

    if quantity_changed < 0 and abs(quantity_changed) > warehouse_quantity:
        error(f"Sorry you only have {warehouse_quantity} of item {item_id} in the warehouse.")
        return

    if box_quantity > warehouse_quantity + quantity_changed:
        error(f"You would have more {name} in the box than the warehouse if you did this")
        #print(f"Box has {box_quantity}, warehouse has {warehouse_quantity}")
        return

    recalculate_inventory(con, "warehouse",  item_id, quantity_changed)

    sql = (f"insert into warehouse_transactions (item_id, quantity_changed) "
           f"values ({item_id}, {quantity_changed})")

    con.cursor().execute(sql)
    con.commit()

    item_id, item_name, quantity = get_item_quantity(con,"warehouse", item_id)
    print(f"Warehouse now has {quantity} {item_name} id {item_id}")

def check_cmd_line(cmd):

    item_id = -1
    quantity = -1
    sticker = 0

    matches = re.finditer(r"\b([a-z]+)\d+\b", cmd, flags=re.IGNORECASE)
    arg_count = 0
    for arg_count, m in enumerate(matches):
        if m.group(1) not in ('i', 'q', 's'):
            error("invalid variable, must be i, q or s")
            return item_id, quantity, sticker

    if arg_count > 2:
        error("Invalid command, too many variables")
        return item_id, quantity, sticker

    # check for valid item id
    matches = re.findall(r"\bi\d+\b", cmd, flags=re.IGNORECASE)
    if len(matches) == 1:
        item_id = int(matches[0][1:])

    matches = re.findall(r"\bq-?\d+\b", cmd, flags=re.IGNORECASE)
    if len(matches) == 1:
        quantity = int(matches[0][1:])

    elif quantity ==  0:
        error("Zero quantity?")

    matches = re.findall(r"\bs\d+\b", cmd, flags=re.IGNORECASE)
    if len(matches) == 1:
        sticker = int(matches[0][1:])

    return item_id, quantity, sticker


def box_transaction(con, cmd):

    item_id, quantity_changed, sticker = check_cmd_line(cmd)
    if item_id <= 0:
        error("Bad command, should be badd i# q# [s#]")
        return

    if not item_exists(con, item_id):
        return

    _, _, warehouse_quantity = get_item_quantity(con, "warehouse", item_id)

    if warehouse_quantity == 0:
        error("Add this item to the warehouse first")
        return
    if warehouse_quantity < quantity_changed:
        error(f"Sorry you only have {warehouse_quantity} of item {item_id} in the warehouse.")
        return

    _, _, box_quantity = get_item_quantity(con, "box", item_id)
    if quantity_changed < 0 and abs(quantity_changed) > box_quantity:
        error(f"Sorry you only have {box_quantity} of item {item_id} in the box.")
        return

    needs_sticker = item_needs_sticker(con, item_id)
    if not sticker and needs_sticker:
        error("This item needs a sticker.")
        return

    if sticker and not needs_sticker:
        error("This item should not have a sticker.")
        return

    # if you have a sticker number the quantity must be 1 or -1
    if sticker > 0 and abs(quantity_changed) > 1:
        error("A sticker item can only add or remove one unit")
        return

    if sticker > 0 and quantity_changed > 0:
        res = con.cursor().execute(f"select i.item_id, i.item_name from box_inventory b"
                                   f" join items i on b.item_id = i.item_id where sticker={sticker}")
        row = res.fetchone()
        if row:
            item_id, item_name = row
            print(f"There is already an item in the box with sticker {sticker}: {item_name} (id {item_id})")
            return

    success = recalculate_inventory(con, table_type="box",  item_id=item_id, quantity_changed=quantity_changed, sticker=sticker)
    if not success:
        return

    if quantity_changed < 0:
        recalculate_inventory(con, table_type="warehouse",  item_id=item_id, quantity_changed=quantity_changed)

    sql = (f"insert into box_transactions (item_id, quantity_changed, sticker) "
           f"values ({item_id}, {quantity_changed}, {sticker})")

    con.cursor().execute(sql)
    con.commit()

    for table_type in ("warehouse", "box"):
        item_id, item_name, quantity = get_item_quantity(con, table_type, item_id)
        print(f"{table_type.title()} now has {quantity} {item_name} id {item_id}")


def show_restock(con: Connection, table_type):
    print("---------------------------------")
    print(f"{table_type.upper()} OUT OF STOCK")
    print("---------------------------------")

    sql = (f"select i.item_id, item_name, sum(quantity) as qsum from {table_type}_inventory w "
           f"join items i  on w.item_id = i.item_id group by 1,2 having qsum = 0")

    res = con.cursor().execute(sql)
    rows = res.fetchall()

    if not rows:
        print(f"No items to restock in {table_type}_inventory")
        return

    for row in rows:
        item_id, name, quantity = row
        print(f"id {item_id} {name}, units: {quantity}")


def show_inventory(con: Connection, table_type, cmd=""):

    list_by_stickers=False
    ar = cmd.split(" ")
    if table_type== "box" and  len(ar) == 2 and ar[1].startswith("sticker"):
        list_by_stickers = True

    item_to_search_for = ""
    if len(ar) == 2 and not re.search("[^0-9]", ar[1]):
        item_to_search_for = ar[1]
        if not item_exists(con, item_to_search_for):
            return

    print("---------------------------------")
    print(f"{table_type.upper()} INVENTORY")
    print("---------------------------------")

    if table_type == "box" and  list_by_stickers:
        sql = f"select i.item_id, item_name, sticker, sum(quantity) from {table_type}_inventory w "

    else:
        sql = f"select i.item_id, item_name, 0 as sticker, sum(quantity) from {table_type}_inventory w "


    sql +=  f"join items i on w.item_id = i.item_id where quantity > 0 "
    if item_to_search_for:
        sql +=  f" and i.item_id = {item_to_search_for} "

    sql += " group by 1,2,3"

    res = con.cursor().execute(sql)
    rows = res.fetchall()

    if not rows:
        print(f"No items in {table_type}_inventory")
        return

    for row in rows :
        item_id, name, sticker, quantity  = row
        line = f"id {item_id} {name}, units: {quantity}"
        if sticker:
            line += f", sticker: {sticker}"

        print(line)




def show_transactions(con: Connection, table_type, cmd):

    limit=1000
    ar = cmd.split(" ")
    if len(ar) == 2:
        limit = ar[1]

    if table_type == "box":
        sql = f"select i.item_id, item_name, quantity_changed, sticker, last_updated from {table_type}_transactions w "
    else:
        sql =f"select i.item_id, item_name, quantity_changed, 0 as sticker, last_updated from {table_type}_transactions w "

    sql += f"join items i  on w.item_id = i.item_id order by last_updated desc limit {limit}"

    res = con.cursor().execute(sql)

    n = 0
    for n, row in enumerate(res.fetchall()):
        item_id, name, quantity, sticker, last_updated = row
        sticker_str = ""
        if sticker != 0:
            sticker_str = f"sticker: {sticker}"
        print(f"id {item_id} {name}: {quantity} {sticker_str} {eastern_time(last_updated)}")

    print(n+1, "rows")

def execute_sql(con,cmd):

    sql = cmd[4:]
    res = con.cursor().execute(sql)

    for row in res.fetchall():
        print(row)

    con.commit()
    print("done")


def totals(con):

    sql = ("select i.item_id, item_name, sum(quantity_changed) qsum "
           "from box_transactions b join items i on b.item_id = i.item_id"
           " where quantity_changed < 0 group by 1,2 having qsum < 0 order by qsum desc")

    res = con.cursor().execute(sql)

    if not res:
        print("No items were distributed")
        return

    print("We distributed:")
    for row in res.fetchall():
        _, item_name, quantity = row
        print(f"{abs(quantity)} {item_name}")


def dump_to_text(con):

    date_str = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    with open(f"dump_{date_str}.txt", 'w') as f:

        tables = ("items", "box_inventory", "warehouse_inventory", "box_transactions", "warehouse_transactions")
        for table in tables:
            f.write("-------------------------------------------------------\n")
            f.write(f"              {table.upper()}\n")
            f.write("-------------------------------------------------------\n\n")

            res = con.cursor().execute(f"select * from {table}")
            rows = res.fetchall()
            for row in rows:
                f.write(f"{'\t'.join([str(v) for v in row])}\n")


def restock_by_sticker(con):

    stickers = set()
    while True:
        sticker = input("Sticker: ").strip()
        if re.search("[^0-9]", sticker):
            print("Numbers only")
            continue

        if not sticker:
            break

        stickers.add(int(sticker))

    if not stickers:
        return

    # now we have the list of stickers we found in the box
    # lets review that these are the items we found
    sql = (f"select i.item_id, item_name, sticker from box_inventory b join "
           f" items i on b.item_id=i.item_id where sticker <> 0 "
           f"and quantity > 0 order by sticker, item_name")

    found_stickers =  []
    removed_stickers = []

    res = con.cursor().execute(sql)
    for row in res.fetchall():
        item_id, item_name, box_sticker = row
        if box_sticker in stickers:
            stickers.remove(box_sticker)
            found_stickers.append((item_id, item_name, box_sticker))
        else:
            removed_stickers.append((item_id, item_name, box_sticker))

    if stickers:
        st = ', '.join([str(x) for x in stickers])
        print(f"These stickers aren't there! {st}")
        return

    print("So these items are in the box: ")
    for item_id, name, sticker in found_stickers:
        print(f"id {item_id} {name}, sticker: {sticker}")

    print("\nAnd these items were removed from the box: ")
    for item_id, name, sticker in removed_stickers:
        print(f"id {item_id} {name}, sticker: {sticker}")

    confirm = input("type YES to confirm: ")
    if confirm != "YES":
        print("ok, nevermind")
        return

    for item_id, _, sticker in removed_stickers:
        box_transaction(con, f"badd i{item_id} s{sticker} q-1")

    print("done")


def restock_no_sticker(con):

    res = con.cursor().execute("select i.item_id, item_name, quantity from items i"
                               " join box_inventory b on b.item_id = i.item_id"
                               " where needs_sticker=0 and quantity>0")

    items_changed_quantity = []
    for row in res.fetchall():
        item_id, name, quantity = row
        new_quantity = input(f"How many {name} (had {quantity}):").strip()

        if re.search("[^0-9]", new_quantity):
            print("Numbers only")
            continue

        if new_quantity == "" or int(new_quantity) == quantity:
            continue
        items_changed_quantity.append((item_id, name, quantity, new_quantity))

    if not items_changed_quantity:
        print("No changes to non-stickered items")
        return

    else:
        print("We removed: ")
        removed = []
        for item_id, name, quantity, new_quantity in items_changed_quantity:
            items_removed = quantity - int(new_quantity)
            print(f"{items_removed} units {name}, now have {new_quantity}")
            removed.append( (item_id, items_removed))

    confirm = input("Type YES to confirm: ")
    if confirm != "YES":
        print("ok, nevermind")
        return

    for item_id, items_removed in removed:
        event_handler(con, f"badd i{item_id} q-{items_removed} s0")


def event_handler(con, cmd):

    if cmd.startswith("list"):
        list_items(con, cmd)

    elif cmd.startswith("wadd"):
        warehouse_transaction(con, cmd)

    elif cmd.startswith("badd"):
        box_transaction(con, cmd)

    elif cmd.startswith("bi"):
        show_inventory(con, "box", cmd)

    elif cmd.startswith("wi"):
        show_inventory(con, "warehouse", cmd)

    elif cmd.startswith("bt"): #, "bshow", "btrans"):
        show_transactions(con, "box", cmd)

    elif cmd.startswith("wt"): #, "wshow", "wtrans"):
        show_transactions(con, "warehouse", cmd)

    elif cmd.startswith("sql"):
        execute_sql(con, cmd)

    elif cmd == "clear":
        clear_all_tables(con)

    elif cmd == "dump":
        dump_to_text(con)

    elif cmd in ("br", "box restock"):
        show_restock(con, "box")

    elif cmd in ("wr", "warehouse restock"):
        show_restock(con, "warehouse")

    elif cmd in ("restock nosticker", "restock nonsticker"):
        restock_no_sticker(con)

    elif cmd == "restock sticker":
        restock_by_sticker(con)

    elif cmd.startswith("total"):
        totals(con)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help="database name, default is minipantry.db", default="minipantry.db")

    args = parser.parse_args()

    print("IT'S INVENTORY TIME!")

    db = "minipantry.db"
    if args.d.lower() != db:
        print(f"**** Database is {args.d} *****")

    con = sqlite3.connect(args.d)

    while True:

        cmd = input("> ")
        cmd = re.sub(r"\s+", " ", cmd)
        cmd = cmd.lower().strip()

        if cmd in ('q', 'quit', 'exit'):
            break

        event_handler(con, cmd)


if __name__ == "__main__":
    main()