import os.path
import sqlite3
from sqlite3 import Connection
import argparse
import common_utils
import re
from common_utils import error, get_item_name_quantity, item_exists, check_cmd_line
import show_utils


def item_needs_sticker(con, item_id):
    res = con.cursor().execute(f"select needs_sticker from items where item_id = {item_id}")
    needs_sticker = res.fetchone()[0]

    return needs_sticker


def confirm(con, item_id, sticker=None, quantity=None):
    res = con.cursor().execute(f"select item_name from items where item_id = {item_id}")
    row = res.fetchone()
    if not row:
        error(f"No item id {item_id}")
        return False

    item_name = row[0]

    message = f"Item is {item_name}"
    if sticker:
        message += f", sticker: {sticker}"
    if quantity:
        message += f" quantity: {quantity}"

    message += " correct? [Yn]:  "
    ok = input(message)
    return ok == "Y"


def recalculate_inventory(con: Connection, table_type, item_id: int, quantity_changed: int, sticker: int = 0):
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


def warehouse_input(con: Connection, cmd: str = None):

    # if there are space-separated arguments, we're entering manually

    if re.search(r"\s", cmd):
        item_id, quantity_changed, _ = check_cmd_line(cmd)
        if item_id <= 0 or quantity_changed == 0:
            error("Bad command, should be wadd i# q#")
            return

        if confirm(con, item_id, quantity=quantity_changed):
            warehouse_action(con, item_id, quantity_changed)

    else:
        items = {}
        while True:
            # TODO currently no way to remove item via scanner
            item_id = input("Scan item barcode: ")

            if not item_id:
                break

            if item_id not in items:
                items[item_id] = 0
            items[item_id] += 1

        for item_id, quantity in items.items():
            if confirm(con, item_id, quantity=quantity):
                warehouse_action(con, item_id, quantity)


def warehouse_action(con: Connection, item_id, quantity_changed):
    name, box_quantity = get_item_name_quantity(con, "box", item_id)
    _, warehouse_quantity = get_item_name_quantity(con, "warehouse", item_id)

    if quantity_changed < 0 and abs(quantity_changed) > warehouse_quantity:
        error(f"Sorry you only have {warehouse_quantity} of item {item_id} in the warehouse.")
        return

    if box_quantity > warehouse_quantity + quantity_changed:
        error(f"You would have more {name} in the box than the warehouse if you did this")
        # print(f"Box has {box_quantity}, warehouse has {warehouse_quantity}")
        return

    recalculate_inventory(con, "warehouse", item_id, quantity_changed)

    sql = (f"insert into warehouse_transactions (item_id, quantity_changed) "
           f"values ({item_id}, {quantity_changed})")

    con.cursor().execute(sql)
    con.commit()

    item_name, quantity = get_item_name_quantity(con, "warehouse", item_id)
    print(f"Warehouse now has {quantity} {item_name} id {item_id}")


def box_input(con: Connection, cmd: str = None, do_confirm=True):
    # if there are space-separated arguments

    if re.search(r"\s", cmd):

        item_id, quantity_changed, sticker = check_cmd_line(cmd)
        if item_id <= 0 or quantity_changed == 0:
            error("Bad command, should be badd i# q# [s#]")
            return

        add_item = False
        if re.match(".add", cmd, flags=re.IGNORECASE):
            add_item = True

        if not do_confirm or confirm(con, item_id, sticker):
            box_action(con, item_id, quantity_changed, sticker=sticker, add_item=add_item)

    else:
        id_pairs = []
        while True:
            # TODO currently no way to remove item via scanner
            item_id = input("Scan item type barcode: ")
            if not item_id:
                break

            sticker = input("Scan ID sticker barcode: ")
            try:
                id_pairs.append((int(item_id), int(sticker)))
            except ValueError as e:
                error(f"Not a number: {e}")

        for item_id, sticker in id_pairs:
            if not do_confirm or confirm(con, item_id, sticker=sticker):
                box_action(con, item_id, 1, sticker, True)


def box_action(con: Connection, item_id, quantity_changed, sticker, add_item: bool):
    if not item_exists(con, item_id):
        return

    _, warehouse_quantity = get_item_name_quantity(con, "warehouse", item_id)
    _, box_quantity = get_item_name_quantity(con, "box", item_id)

    if warehouse_quantity == 0:
        error("Add this item to the warehouse first")
        return

    # CHECK THIS, this needs to take into account NEW quantity
    # so if you add an item to the box, and it brings the total items to more
    # than in the warehouse
    # NOT just that you're adding one at a time
    if warehouse_quantity < (quantity_changed + box_quantity):
        error(f"Sorry you only have {warehouse_quantity} of item {item_id} in the warehouse.")
        return

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

    # don't really need these next two checks I think
    if not add_item and quantity_changed > 0:
        print("Use negative quantity for removing items")
        return

    if add_item and quantity_changed < 0:
        print("Quantity must be positive for adding an item.")
        return

    if add_item and sticker > 0 and quantity_changed > 0:
        res = con.cursor().execute(f"select i.item_id, i.item_name from box_transactions b"
                                   f" join items i on b.item_id = i.item_id where sticker={sticker}")
        row = res.fetchone()
        if row:
            item_id, item_name = row
            print(f"There is or was already an item in the box with sticker {sticker}: {item_name} (id {item_id})")
            return

    success = recalculate_inventory(con, table_type="box", item_id=item_id, quantity_changed=quantity_changed,
                                    sticker=sticker)
    if not success:
        return

    if quantity_changed < 0:
        recalculate_inventory(con, table_type="warehouse", item_id=item_id, quantity_changed=quantity_changed)

    sql = (f"insert into box_transactions (item_id, quantity_changed, sticker) "
           f"values ({item_id}, {quantity_changed}, {sticker})")

    con.cursor().execute(sql)
    con.commit()

    for table_type in ("warehouse", "box"):
        item_name, quantity = get_item_name_quantity(con, table_type, item_id)
        print(f"{table_type.title()} now has {quantity} {item_name} id {item_id}")


def inventory_by_sticker(con, stickers=None):
    sql = (f"select i.item_id, item_name, sticker from box_inventory b join "
           f" items i on b.item_id=i.item_id where sticker <> 0 "
           f"and quantity > 0 order by sticker, item_name")

    res = con.cursor().execute(sql)
    all_box_items = []
    current_stickers = set()
    for row in res.fetchall():
        all_box_items.append(row)
        current_stickers.add(row[2])

    if not stickers:
        stickers = set()

        while True:
            stk = input("Sticker: ").strip()
            if not stk:
                break

            if re.search("[^0-9]", stk):
                print("Numbers only")
                continue

            stickers.add(int(stk))

    not_found_stickers = set()
    for stk in stickers:

        if int(stk) not in current_stickers:
            print(f"Sticker {stk} isn't there")
            not_found_stickers.add(stk)
            continue

    stickers -= not_found_stickers
    if not stickers:
        return

    found_stickers = []
    removed_stickers = []

    for row in all_box_items:
        item_id, item_name, box_sticker = row
        if box_sticker in stickers:
            stickers.remove(box_sticker)
            found_stickers.append((item_id, item_name, box_sticker))
        else:
            removed_stickers.append((item_id, item_name, box_sticker))

    print("So these items are in the box: ")
    for item_id, name, sticker in found_stickers:
        print(f"id {item_id} {name}, sticker: {sticker}")

    # TODO why do we have two confirmations here?
    print("\nConfirm each item to remove:")
    for item_id, name, sticker in removed_stickers:

        ok = input(f"\nRemove id {item_id} {name}, sticker: {sticker}? [Yn]")
        if ok == "Y":
            box_input(con, f"brem i{item_id} s{sticker} q-1", do_confirm=False)
            print(f"Removed {name}")

        else:
            print("Kept")

    print("done")


def inventory_no_sticker(con):
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
            removed.append((item_id, items_removed))

    ok = input("Type YES to confirm: ")
    if ok != "YES":
        print("ok, nevermind")
        return

    for item_id, items_removed in removed:
        event_handler(con, f"brem i{item_id} q-{items_removed}")


def load_restock_file(con, cmd):
    tokens = cmd.split(" ")

    file = "restock_file.txt"
    if len(tokens) > 2:
        file = tokens[1].strip()

    if not os.path.exists(file):
        error(f"File {file} not found")
        return

    stickers = set()
    with open(file) as f:
        for n, line in enumerate(f.readlines()):
            sticker = line.strip()

            if not sticker:
                continue

            if re.search(r"\D", sticker):
                print(f"Non-numeric value on line {n}: {line}")
                continue

            stickers.add(int(sticker))

    inventory_by_sticker(con, stickers)


def event_handler(con, cmd):
    if cmd.startswith("last"):  # last sticker:
        show_utils.show_max_sticker(con)

    if cmd.startswith("whatis"):
        common_utils.get_item_by_id(con, cmd)

    if cmd.startswith("list"):
        show_utils.list_items(con, cmd)

    elif cmd.startswith("hide") or cmd.startswith("unhide"):
        common_utils.hide(con, cmd)

    elif cmd.startswith("putback"):
        put_back(con, cmd)

    elif cmd.startswith("wadd"):
        warehouse_input(con, cmd)

    elif cmd.startswith("badd"):
        box_input(con, cmd)

    elif cmd.startswith("brem"):  # boxremove
        box_input(con, cmd)

    elif cmd.startswith("bi"):
        show_utils.show_inventory(con, "box", cmd)

    elif cmd.startswith("wi"):
        show_utils.show_inventory(con, "warehouse", cmd)

    elif cmd.startswith("bt"):  # , "bshow", "btrans"):
        show_utils.show_transactions(con, "box", cmd)

    elif cmd.startswith("wt"):  # , "wshow", "wtrans"):
        show_utils.show_transactions(con, "warehouse", cmd)

    elif cmd.startswith("sql"):
        common_utils.execute_sql(con, cmd)

    elif cmd == "clear":
        common_utils.clear_all_tables(con)

    elif cmd == "dump":
        show_utils.dump_to_text(con)

    elif cmd in ("br", "box restock"):
        show_utils.show_box_restock(con)

    elif cmd in ("wr", "warehouse restock"):
        show_utils.show_warehouse_restock(con)

    elif cmd in ("restock nosticker", "restock nonsticker"):
        inventory_no_sticker(con)

    elif cmd == "restock sticker":
        inventory_by_sticker(con)

    elif cmd == "restock file":
        load_restock_file(con, cmd)

    elif cmd.startswith("summary"):
        show_utils.totals(con)

    elif cmd.startswith("total"):
        show_utils.totals(con, summarized=False)

    elif cmd.startswith("diapers"):
        show_utils.totals(con, summarized=False, diapers_only=True)


def put_back(con, cmd):
    # parse out the sticker
    item_id, quantity, sticker = check_cmd_line(cmd)
    if not sticker or item_id == -1:
        error("Need a valid sticker and item: sNNN iNN")
        return

    # check if it existed and if it isn't there now
    sql = f"select quantity from box_inventory where sticker={sticker} and item_id={item_id}"
    res = con.cursor().execute(sql)
    row = res.fetchone()
    if row is None:
        error(f"Item {item_id} sticker {sticker} was not in the box.")
        return

    quantity = int(row[0])
    if int(quantity) > 0:
        error(f"Item {item_id} with sticker {sticker} is still there, you can't put it back.")
        return

    # update box inventory and set quantity back to 1 for that sticker
    con.cursor().execute(f"update box_inventory set quantity=1 where sticker={sticker}")

    # update warehouse inventory and add 1 back to quantity
    con.cursor().execute(f"update warehouse_inventory set quantity=quantity+1 where item_id={item_id}")

    # delete box transaction row where you removed that item
    con.cursor().execute(f"delete from box_transactions where quantity_changed=-1 and sticker={sticker}")

    con.commit()

    print("done")


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
