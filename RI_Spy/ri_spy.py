import sqlite3
import argparse
from observations import stone_groups, Color, Phenomenon, Assembled, Transparency, OpticNature

stone_group_dict = {}
for sg in stone_groups:
    stone_group_dict[sg.name] = sg


class LookupObj:
    def __init__(self):
        self.high_ri = ""
        self.low_ri = ""
        self.spot_ri = ""
        self.optic_nature = ""
        self.color = ""
        self.transparency = ""
        self.phenomenon = ""
        self.assembled = ""


def question(question_text: str, enum, default="", required=False):
    values = []

    for x in enum:
        values.append(x.value)

    while True:

        answer = input(f"{question_text}: {default}")
        answer = answer.upper().strip()
        if not answer and required and default:
            return default

        if not answer and not required:
            return answer

        if answer not in values:
            print(f"Choices are: {", ".join(values)}")
            continue

        return answer


def get_stone_group(color: str = None, phenomenon: str = None, assembled: str = "N", transparency: str = None):

    a: Assembled = Assembled[assembled] if assembled else None
    p: Phenomenon = Phenomenon[phenomenon] if assembled else None
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
        if group.is_assembled() or group.is_phenomenal():
            continue
        if c and group.has_primary_color(c):
            subset.add(group)
        if t and group.has_transparency(t):
            tp_subset.add(group)

    if not subset:
        return tp_subset
    if not tp_subset:
        return subset

    return subset.intersection(tp_subset)


def get_float(prompt: str, default: (str | float) = "") -> float:
    while True:
        str_value = input(f"{prompt}: {default}")
        try:
            if not str_value.strip():
                if default:
                    return float(default)
                return 0

            if str_value.upper().strip() in ("OTL", "BB"):
                return 1.8

            return float(str_value)

        except ValueError:
            print("Enter a decimal value or leave blank")


def get_observations(lk: LookupObj = None):

    if not lk:
        lk = LookupObj()

    while True:
        lk.high_ri = get_float("High RI", lk.high_ri)
        lk.low_ri = get_float("Low RI", lk.low_ri)
        ri_str = f"HI: {lk.high_ri}"
        if lk.low_ri:
            ri_str += f", LO: {lk.low_ri}, BIRE: {round(lk.high_ri - lk.low_ri, 3)}"

        if not (lk.high_ri or lk.low_ri):
            lk.spot_ri = get_float("Spot RI", lk.spot_ri)
            ri_str = f"Spot: {lk.spot_ri}"

        lk.optic_nature = question("Optic Nature", OpticNature, default=lk.optic_nature)
        lk.color = question("Primary color", Color, default=lk.color, required=True)
        lk.transparency = question("Transparency", Transparency, default=lk.transparency, required=True)
        lk.phenomenon = question("Phenomenon", Phenomenon, default=lk.phenomenon)
        lk.assembled = question("Assembled?", Assembled, default=lk.assembled)

        print(f"{ri_str}\n{lk.optic_nature}\n"
              f"Color: {lk.color}\n"
              f"Transparency: {lk.transparency}\n"
              f"Phenomenon: {lk.phenomenon}\n"
              f"Assembled: {lk.assembled}")

        ok = input("N to do over, otherwise enter to accept: ")

        if ok.upper() != "N":
            return lk


def lookup_stones(db_name, lk: LookupObj, lk_stone_groups: set):

    con = sqlite3.connect(db_name)
    con.row_factory = sqlite3.Row

    groups = [f"'{g.name.lower()}'" for g in lk_stone_groups]

    sql = (f"select ri_text, optic_nature, gem_name, page from refractive_index "
           f"where color_family in ({', '.join(groups)}) ")

    if lk.spot_ri:
        sql += f" and {lk.spot_ri} between low_ri and high_ri "
    elif lk.high_ri:
        if lk.low_ri:
            # DR
            sql += f" and high_ri <= {lk.high_ri} and low_ri >= {lk.low_ri} "
        else:
            # SR
            sql += f" and high_ri <= {float(lk.high_ri) + 0.01} and low_ri >= {float(lk.high_ri) - 0.01} "

    if lk.optic_nature:
        sql += f" and optic_nature = '{lk.optic_nature}'"

    res = con.execute(sql)
    rows = res.fetchall()
    if not rows:
        print("No results :( ")

    for row in rows:
        print(f"{row['ri_text']}\t{row['optic_nature']}\t{row['gem_name']}\t{row['page']}")


def main():
    db = "ri_spy.db"

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", help=f"database name, default is {db}", default=db)

    args = parser.parse_args()

    print("RI SPY")

    if args.d.lower() != db:
        print(f"**** Database is {args.d} *****")

    lk = LookupObj()

    while True:
        try:
            lk = get_observations(lk)

            groups = get_stone_group(lk.color, lk.phenomenon, lk.assembled, lk.transparency)
            lookup_stones(args.d, lk, groups)

            out = input("Q to quit, N for new stone, or enter to adjust: ").strip().upper()
            if out == 'Q':
                return
            if out == "N":
                lk = LookupObj()

        except KeyboardInterrupt:
            print("\nBye")


if __name__ == "__main__":
    main()
