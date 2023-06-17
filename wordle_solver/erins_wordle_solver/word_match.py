from nltk.corpus import words as default_words
from collections import Counter
import re
from operator_class import Operator


class WordMatch:

    def __init__(self, word_len: int):

        self.guesses = None
        self.letter_freq = None
        self.word_len = word_len
        self.reset()

    def reset(self):

        self.guesses = set()
        self.letter_freq = {}

        letter_counts = Counter()
        all_letters = 0

        # now index the words, only the ones for the specified word length
        for n, corpus in enumerate([default_words]):

            for word in corpus.words():
                word = word.lower()
                if len(word) != self.word_len or re.search("[^a-z]", word):
                    continue

                self.guesses.add(word)

                for letter in word:
                    # keep statistics to calculate letter frequency later
                    # (we could just also use letter frequency for English overall)
                    letter_counts[letter] += 1
                    all_letters += 1

        for letter, count in letter_counts.items():
            self.letter_freq[letter] = count / all_letters

    def run_operators(self, pattern):

        if Operator.is_exclude(pattern):

            # create a character class of all the letters to exclude, and remove them
            regex = f"[{pattern[1:]}]"
            excluded_words = set()
            for word in self.guesses:
                if re.search(regex, word):
                    excluded_words.add(word)
            self.guesses -= excluded_words

        if Operator.is_unknown_position(pattern):

            words_to_exclude = set()

            # limit the guesses to those that contain these letters
            # all of them but in any order
            for letterpos in re.findall(f"[a-z][1-{self.word_len}]*", pattern[1:]):
                letter = letterpos[0]
                exclude_pos = None
                if len(letterpos) > 1:
                    exclude_pos = int(letterpos[1:])

                # this does mean you iterate through guesses for each unknown-position letter
                # but most of the time there should be only 1 anyway
                for guess in self.guesses:
                    found_at = guess.find(letter)
                    # remember the position given by the user is 1-based
                    if found_at == -1 or \
                            (exclude_pos is not None and found_at == exclude_pos - 1):
                        words_to_exclude.add(guess)

            self.guesses -= words_to_exclude

        if Operator.is_exclude(pattern) or Operator.is_unknown_position(pattern):
            print(f"{len(self.guesses)} possibilities remaining")

    def get_guess_list(self, pattern):

        guesses = set()
        for word in self.guesses:
            if re.search(pattern, word):
                guesses.add(word)

        freq_letter_words = {}
        for guess in guesses:

            # we try to maximize score by number of different letters
            # and letters with highest frequency
            # so you try the word that will rule out the most other words
            found = set()
            found.update(guess)
            unique_score = len(found)

            freq_score = 0
            for letter in found:
                freq_score += self.letter_freq[letter]

            # this is not scientific
            score = round(freq_score * unique_score, 3)

            if score in freq_letter_words:
                freq_letter_words[score].append(guess)
            else:
                freq_letter_words[score] = [guess]

        if not guesses:
            print("We got nothing")

        return freq_letter_words
