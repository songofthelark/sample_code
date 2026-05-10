from zoneinfo import ZoneInfo
from sqlite3 import Connection
from datetime import datetime
import re


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

    matches = re.findall(r"\bs\d+\b", cmd, flags=re.IGNORECASE)
    if len(matches) == 1:
        sticker = int(matches[0][1:])
        if sticker <= 0:
            error(f"Invalid sticker number {sticker}")
            return item_id, quantity, sticker

        if cmd.startswith("badd"):
            quantity = 1
        elif cmd.startswith("brem"):
            quantity = -1
    else:
        # if there isn't a sticker, we need to have quantity
        matches = re.findall(r"\bq-?\d+\b", cmd, flags=re.IGNORECASE)
        if len(matches) == 1:
            quantity = int(matches[0][1:])

    if quantity == 0:
        error("Zero quantity?")

    return item_id, quantity, sticker


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


def eastern_time(str_date):
    dateformat = "%Y-%m-%d %H:%M:%S"
    naive_dt = datetime.strptime(str_date, dateformat)
    utc_dt = naive_dt.replace(tzinfo=ZoneInfo("UTC"))
    eastern_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))

    return eastern_dt.strftime(dateformat)


def error(msg):
    print("FAILED", msg)


def execute_sql(con, cmd):
    sql = cmd[4:]
    res = con.cursor().execute(sql)

    for row in res.fetchall():
        print(row)

    con.commit()
    print("done")


def hide(con, cmd):
    ar = cmd.split(" ")
    if len(ar) != 2:
        print("Need an item id")
        return

    text, item_id = ar
    if not item_exists(con, item_id):
        return

    hide_item = 1
    if text == "unhide":
        hide_item = 0

    sql = f"update items set hide={hide_item} where item_id={item_id};"
    con.cursor().execute(sql)
    print("Done")


def item_exists(con: Connection, item_id) -> bool:
    res = con.cursor().execute(f"select count(*) from items where item_id = {item_id}")
    count = res.fetchone()[0]

    if not count:
        error(f"No item id {item_id}")

    return count > 0


def get_item_name_quantity(con, table_type, item_id):
    s = (f"select i.item_id, item_name, sum(quantity) from {table_type}_inventory x "
         f"join items i on i.item_id = x.item_id where i.item_id={item_id} group by i.item_id, item_name")

    res = con.cursor().execute(s)
    row = res.fetchone()
    if row:
        return row[1], row[2]
    return "(none)", 0


def get_item_by_id(con, cmd):
    item_id, _, sticker = check_cmd_line(cmd)
    if not sticker and not item_id:
        error("Must specify item or sticker: sNNN or iNN")
        return

    # check if it existed and if it isn't there now
    sql = (f"select b.item_id, item_name from box_inventory b join "
           f"items i on i.item_id=b.item_id where ")

    if sticker:
        sql += f"sticker={sticker}"
    else:
        sql += f"b.item_id={item_id}"

    res = con.cursor().execute(sql)
    row = res.fetchone()
    if row is None:
        error(f"Not found")
        return

    print(f"Item {row[0]}: {row[1]}")

    if sticker:
        res = con.cursor().execute(
            f"select quantity_changed, last_updated from box_transactions where sticker={sticker}")
        rows = res.fetchall()
        for row in rows:
            quantity, updated = row
            print(f"Quantity: {quantity} on {updated}")
