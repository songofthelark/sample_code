from __future__ import annotations
from itertools import combinations
import argparse
import signal


def handler(_, __):
    exit(1)


signal.signal(signal.SIGINT, handler)


class Person:
    def __init__(self, name, speed):
        self.name = name
        self.speed = speed

    def __str__(self):
        return self.name


A = Person('A', 1)
B = Person('B', 2)
C = Person('C', 5)
D = Person('D', 10)


max_group_size = 2
cost_cutoff = 17

starting_canyon_left = {A, B, C, D}
canyon_left = starting_canyon_left.copy()
canyon_right = set()

all_traversals = []

verbose = False


class Traversal:

    def __init__(self, traversal: Traversal = None):
        self.sequence = []
        self.cost = 0

        if traversal:
            self.sequence = traversal.sequence.copy()
            self.cost = traversal.cost

    def add(self, group):
        _, slowest = person_speeds(group)
        self.sequence.append(group)
        self.cost += slowest.speed

    def get_last_group(self):
        if self.sequence:
            return self.sequence[-1]
        return None

    def remove_last_group(self):
        if not self.sequence:
            return None

        group = self.sequence.pop()
        _, slowest = person_speeds(group)
        self.cost -= slowest.speed
        return group

    def __len__(self):
        return len(self.sequence)

    def get_sequence_string(self):
        out = []
        for n, group in enumerate(self.sequence):
            x = get_name_string(group)
            if n % 2:
                x += "<--"
            else:
                x += "-->"

            out.append(x)
        return ", ".join(out)

    def write(self):

        # path = f"Path ID: {str(id(self))}\n"
        path = self.get_sequence_string()
        path += f"\nCost: {self.cost}\n"

        return path

    def reenact(self):

        left = set()
        for x in starting_canyon_left:
            left.add(x.name)

        right = set()
        out = []

        for n, group in enumerate(self.sequence):

            group_names = set()
            for x in group:
                group_names.add(x.name)

            if n % 2 == 0:
                if not group_names.issubset(left):
                    out.append(f"ERROR {group_names} not in left")
                    break

                for p in group_names:
                    left.remove(p)
                    right.add(p)

                out.append(f"{n} --> {get_name_string(group)}")
            else:
                if not group_names.issubset(right):
                    out.append(f"ERROR {group_names} not in right")
                    break

                for p in group_names:
                    right.remove(p)
                    left.add(p)

                out.append(f"{n} <-- {get_name_string(group)}")

            out.append(f" {get_name_string(left)} | {get_name_string(right)}")

        return "\n".join(out)


def person_speeds(persons: list):
    min_speed = 1000  # or whatever max int value is
    max_speed = -1
    fast_person = None
    slow_person = None

    for p in persons:
        if p.speed < min_speed:
            fast_person = p
            min_speed = p.speed
        if p.speed > max_speed:
            slow_person = p
            max_speed = p.speed

    return fast_person, slow_person


def get_name_string(person_list) -> str:
    names = []
    for x in person_list:
        if type(x) == Person:
            names.append(x.name)
        else:
            names.append(x)
    names.sort()

    return ' '.join(names)


def get_crossers(min_group_size, values):
    if max_group_size < min_group_size:
        return []

    combos = {}

    all_combinations = []

    for n in range(min_group_size, max_group_size + 1):
        for combo in combinations(values, n):

            # don't think this makes any difference
            _, slowest = person_speeds(combo)
            if slowest.speed not in combos:
                combos[slowest.speed] = [combo]
            else:
                combos[slowest.speed].append(combo)

            # all_combinations.append(combo)

    # sort by
    speeds = list(combos.keys())
    speeds.sort()
    for speed in speeds:
        all_combinations.extend(combos[speed])

    return all_combinations


def finish(traversal: Traversal):

    if traversal.cost > cost_cutoff:
        return

    global all_traversals
    copy = Traversal(traversal)

    all_traversals.append(copy)
    print(f"{len(all_traversals)}. {traversal.write()}")


def revert_last_to_left(traversal):
    global canyon_left, canyon_right

    group = traversal.remove_last_group()
    if not group:
        if verbose:
            print("Traversal is empty and you're on the left")
        return

    if not group.issubset(canyon_right):
        print(f""""
            ERROR Group {get_name_string(group)} is not in canyon_right!")
            {get_name_string(canyon_left)} | {get_name_string(canyon_right)}
            {traversal.get_sequence_string()}""")

    canyon_left.update(group)
    canyon_right -= group


def revert_last_to_right(traversal):
    global canyon_left, canyon_right

    group = traversal.remove_last_group()
    if not group:
        if verbose:
            print("Traversal is empty and you're on the right")
        return

    if not group.issubset(canyon_left):
        print(f""""
            ERROR Group {get_name_string(group)} is not in canyon_left!")
            {get_name_string(canyon_left)} | {get_name_string(canyon_right)}
            {traversal.get_sequence_string()}""")

    canyon_right.update(group)
    canyon_left -= group


def cross_right(level=1, traversal=None):
    global canyon_left, canyon_right

    if not traversal:
        traversal = Traversal()

    if traversal.cost >= cost_cutoff:
        if verbose:
            print("Not crossing right, aborting due to cost")
        revert_last_to_right(traversal)
        return

    crossers = get_crossers(2, canyon_left)

    for n, group_crossing_right in enumerate(crossers):

        group_crossing_right = set(group_crossing_right)

        if not group_crossing_right.issubset(canyon_left):
            continue

        if verbose:
            # give torch to person with fastest speed
            torch_holder, _ = person_speeds(group_crossing_right)
            print(f"\n'|' {torch_holder} has torch going right")
            print(f"--> {get_name_string(group_crossing_right)} goes right")

        # actual crossing here
        canyon_left -= group_crossing_right
        traversal.add(group_crossing_right)
        canyon_right.update(group_crossing_right)

        if not canyon_left:

            # we finished moving everyone across!
            # store the results
            finish(traversal)

            # now try again for other crossing groups at this level
            # put back the last crossing group so we can try another traversal
            revert_last_to_left(traversal)

        else:

            if verbose:
                print(f"Level {level} Left: {get_name_string(canyon_left)} Right: {get_name_string(canyon_right)}, Going left <--")
                print(traversal.get_sequence_string())

            cross_left(level + 1, traversal)

    revert_last_to_right(traversal)


def cross_left(level, traversal):
    global canyon_left, canyon_right

    if traversal.cost >= cost_cutoff:
        if verbose:
            print("Not crossing left, aborting due to cost")
        revert_last_to_left(traversal)
        return

    crossers = get_crossers(1, canyon_right)

    for group_crossing_left in crossers:

        group_crossing_left = set(group_crossing_left)

        # same people can't go back, that's stupid
        if traversal.get_last_group() == group_crossing_left or not group_crossing_left.issubset(canyon_right):
            continue

        if verbose:
            # give torch to person with fastest speed
            torch_holder, _ = person_speeds(group_crossing_left)
            print(f"\n'|' {torch_holder} has torch going left")
            print(f"<-- {get_name_string(group_crossing_left)} goes left")

        # actual crossing here
        traversal.add(group_crossing_left)
        canyon_right -= group_crossing_left
        canyon_left.update(group_crossing_left)

        if verbose:
            print(f"Level {level} Left: {get_name_string(canyon_left)} Right: {get_name_string(canyon_right)}, Going right -->")
            print(traversal.get_sequence_string())

        cross_right(level + 1, traversal)

    revert_last_to_left(traversal)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='cost_cutoff', required=True, type=int)
    args = parser.parse_args()

    global cost_cutoff
    cost_cutoff = args.c

    cross_right()

    if not all_traversals:
        print("Didn't find anything")
        return

    while True:
        index = input("\nShow details for: ")
        index = int(index)
        if index <= 0 or index > len(all_traversals):
            continue

        traversal = all_traversals[index-1]

        print(traversal.write() + "\n")
        print(traversal.reenact())


if __name__ == "__main__":
    main()
