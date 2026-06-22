import os.path
import sqlite3
from sqlite3 import Connection
import argparse
import re
from observations import stone_groups, Color, Phenomenon, Assembled, Transparency, OpticNature

stone_group_dict = {}
for sg in stone_groups:
    stone_group_dict[sg.name] = sg


def question(attribute_name, attribute_options):
    pass


def get_stone_group(color: str = None, phenomenon: str = None, assembled: str = "N", transparency: str = None):

    a: Assembled = Assembled[assembled]
    p: Phenomenon = Phenomenon[phenomenon]
    c: Color = Color[color]
    t: Transparency = Transparency[transparency]

    # is this efficient? no. do I care? no.

    subset = set()

    if a or p:
        for group in stone_groups:
            if group.is_assembled() or group.has_phenomenon(p):
                subset.add(group)
                return subset

    tp_subset = set()
    for group in stone_groups:
        if c and group.has_primary_color(c):
            subset.add(sg)
        if t and group.has_transparency(t):
            tp_subset.add(t)

    if not subset:
        return tp_subset
    if not tp_subset:
        return subset

    return subset.intersection(tp_subset)


def get_float(prompt: str) -> float:
    while True:
        str_value = input(f"{prompt}: ")
        try:
            if not str_value.strip():
                return 0

            if str_value.upper().strip() in ("OTL", "BB"):
                return 1.8

            return float(str_value)

        except ValueError:
            print("Enter a decimal value or leave blank")


def main():
    db = "ri_spy.db"

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help=f"database name, default is {db}", default=db)

    args = parser.parse_args()

    print("RI SPY")

    if args.d.lower() != db:
        print(f"**** Database is {args.d} *****")

    con = sqlite3.connect(args.d)

    high_ri = get_float("High RI")
    low_ri = get_float("Low RI")
    spot_ri = 0

    if not (high_ri or low_ri):
        spot_ri = get_float("Spot RI")

    while True:

        cmd = input("> ")
        cmd = re.sub(r"\s+", " ", cmd)
        cmd = cmd.lower().strip()

        if cmd in ('q', 'quit', 'exit'):
            break


if __name__ == "__main__":
    main()
