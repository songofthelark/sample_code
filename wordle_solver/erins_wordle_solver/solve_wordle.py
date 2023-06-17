
import nltk
import re
from operator_class import Operator
from word_match import WordMatch
import sys


def signal_handler(sig, frame):
    print('Bye!')
    sys.exit(0)


history = []


def get_input():

    if history:
        print(f"\nHistory: {history}")

    pattern = None
    while not pattern:
        pattern = input("> ")

        # remove any spaces, which are allowed for clarity
        pattern = re.sub(r"\s+", "", pattern)

    return pattern.lower()


def check_pattern(pattern, word_len, show_help=True):
    # build a regular expression for the first character
    ops = []
    for op in Operator:
        ops.append(op.value)

    allowable_start = f"[a-z{''.join(ops)}]"

    def print_help(help_str):
        if show_help:
            print(help_str)

    first_char = pattern[0]
    if not re.fullmatch(allowable_start, first_char):
        print_help(f"""
        Match pattern must start with letter or one of the operators: {" ".join(ops)}""")
        return False

    pattern_help_string = f"""
        If you're putting the pattern here, it must contain {word_len} characters, and the characters
        can only be {Operator.MASK.value} or a letter"""

    try:
        op = Operator(first_char)

        if op == Operator.EXCLUDE:
            # pattern for excluded letters goes !a or !abc
            if re.fullmatch(r"[a-z]+", pattern[1:]):
                return True
            else:
                print_help(f"""
                To specify that one more letters aren't there, start with {Operator.EXCLUDE.value} followed by the letters. 
                Ex: {Operator.EXCLUDE.value}abc to exclude words containing a, b, and c""")
                return False

        if op == Operator.UNKNOWN_POSITION:
            # pattern for unknown-position letters goes ?abc or ?a1b2d3
            if re.fullmatch(fr"([a-z][1-{word_len}]*)+", pattern[1:]):
                return True
            else:
                print_help(f"""
                        To specify the letters are there but you don't know where, 
                        start with {Operator.UNKNOWN_POSITION.value} followed by the letters,
                        Ex: {Operator.UNKNOWN_POSITION.value}def to require words to contain d, e, or f
                        If you want, you can be more specific by saying you know where the letter does NOT appear
                        By putting the number of the yellow box it appears in.  So if you know that "a" appears
                        but not as the first letter, you can put {Operator.UNKNOWN_POSITION.value}a1 """)
                return False

    except ValueError:
        # the first character should have been a period or a letter.  if it was a period, it would have been converted
        # to an operator, so lets make sure it's a letter and not a number or symbol
        if not first_char.isalpha():
            print_help(pattern_help_string)
            return False

    # if the first character is a period or a letter, make sure that it's a valid pattern
    mask_re = f"[{Operator.MASK.value}a-z]" + "{" + str(word_len) + "}"

    if not re.fullmatch(mask_re, pattern):
        print_help(pattern_help_string)
        return False

    return True


def main(word_len=5):
    # download words corpus from nltk
    print("\nDownloading corpus, it may already be here so don't worry if you see something that looks like an error.")
    nltk.download("words")

    print(f"Enter q to quit, {Operator.CLEAR.value} to start over")

    word_match = WordMatch(word_len)
    pattern = get_input()

    # put in the results from wordle
    # dots for each letter, comma and then letters for which we don't know position
    while pattern != "q":

        # * to start over, ! for exclude, ? for unknown

        if pattern == Operator.CLEAR.value:
            word_match.reset()
            history.clear()
            print("Starting fresh!")
            pattern = get_input()
            continue

        if not check_pattern(pattern, word_len):
            pattern = get_input()
            continue

        if Operator.is_exclude(pattern) or Operator.is_unknown_position(pattern):
            history.append(pattern)
            word_match.run_operators(pattern)
            pattern = get_input()
            continue

        # if we got here then we have a legitimate pattern to match

        # rank the guesses by number of frequent letters
        # so we pick the words with the most common letters to try
        ranked = word_match.get_guess_list(pattern)
        rank = len(ranked)
        print("Rank Words")
        for score, choices in sorted(ranked.items()):
            print(rank, choices)
            rank -= 1

        pattern = get_input()


if __name__ == "__main__":
    main()
