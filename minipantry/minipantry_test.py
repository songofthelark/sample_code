import sqlite3
from inventory import clear_all_tables, event_handler

def run_test():
    con = sqlite3.connect(r"C:\Users\coryc\Documents\minipantry_test.db")

    clear_all_tables(con)

    # add 10 each of 3 sizes of diapers
    event_handler(con, "wadd i6 q10")
    event_handler(con, "wadd i7 q10")
    event_handler(con, "wadd i8 q10")

    # add 5 toothbrushes and 8 soaps
    event_handler(con, "wadd i20 q8")
    event_handler(con, "wadd i17 q5")


    test_item(con, "wi", succeed=True,
              check="Check you have 10 each of 3 diaper sizes, 8 soaps and 5 toothbrushes")

    test_item(con, "badd i14 q1", succeed=False, check = "Not in the warehouse")

    test_item(con, "badd i7 q1", False, "No sticker")

    test_item(con, "badd i7 q1 s10", True, check=
    "Check we added 1 unit diapers to box with sticker 10")

    test_item(con, "badd i8 q1 s10", False, check= "Duplicate sticker")

    test_item(con, "badd i20 q1 s11", False, check= "Soap is a non-sticker item")

    test_item(con, "badd i20 q2", True, check="Should have added two soaps to box")

    test_item(con, "badd i20 q-3", False, check="There aren't that many soaps in the box")

    test_item(con,  "badd i20 q-2", True, check ="Six soaps in warehouse 0 in box, right?")

    test_item(con, "wadd i20 q-7", False , check="Can't remove that many soap from warehouse")

    test_item(con, "wadd i20 q-6", True, check="Warehouse now has 0 soap")

    test_item(con, "badd i20 q2", False, check="There's no soap in the warehouse")

    test_item(con, "badd i20 q2", False, check="There's no soap in the warehouse")

    test_item(con, "wr", True, "Warehouse should need to restock soap")

    test_item(con, "br", True, "Box should need to restock soap")

    test_item(con, "badd i7 s11 q-1", False, "Sticker not found")

    test_item(con, "badd i7 s10 q-1", True, "Removed 1 diapers")

    test_item(con, "br", True, "Box should need to restock soap AND diapers size 2")

    test_item(con, "badd i6 q10 s1", False, "Can only add one sticker item at a time")

    event_handler(con, "badd i6 q1 s1")
    event_handler(con, "badd i6 q1 s2")
    event_handler(con, "badd i6 q1 s3")
    event_handler(con, "badd i6 q1 s4")
    event_handler(con, "badd i6 q1 s5")
    event_handler(con, "badd i6 q1 s6")
    event_handler(con, "badd i6 q1 s7")
    event_handler(con, "badd i6 q1 s8")
    event_handler(con, "badd i6 q1 s9")
    event_handler(con, "badd i6 q1 s12")

    test_item(con, "bi", True, "Should have ten stickered diapers size 1 in box")

    test_item(con, "badd i6 q-10 s1", False, "No sticker / can't remove 10 items at once")

    event_handler(con, "badd i6 q-1 s1")
    event_handler(con, "badd i6 q-1 s2")
    event_handler(con, "badd i6 q-1 s3")
    event_handler(con, "badd i6 q-1 s4")
    event_handler(con, "badd i6 q-1 s5")
    event_handler(con, "badd i6 q-1 s6")
    event_handler(con, "badd i6 q-1 s7")
    event_handler(con, "badd i6 q-1 s8")
    event_handler(con, "badd i6 q-1 s9")
    event_handler(con, "badd i6 q-1 s12")

    test_item(con, "bi", True, "No diapers size 2 in box")
    test_item(con, "br", True, "Box needs to restock diapers size 1 and 2 (and soap)")
    test_item(con, "wr", True, "Warehouse needs to restock diapers size 1 and 2 (and soap)")


test_item_count =1
def test_item(con, cmd:str, succeed:bool, check:str):

    print()
    event_handler(con, cmd)
    result = f"\nCMD WAS {cmd}"
    if succeed:
        result += ", should have SUCCEDED"
    else:
        result += ", should have FAILED"
    print(result)

    global test_item_count
    input(f"-- {test_item_count} -- {check}")
    test_item_count += 1


if __name__ == "__main__":
    run_test()