import argparse
from collections import Counter
import string


def encryption(text: str, decoder: dict, task: str = "encrypt") -> str:
    key = {}
    out = []

    # create key according to encryption task
    for orig, tup in decoder.items():
        _, encrypted = tup
        if task == "encrypt":
            key[orig] = encrypted
        else:
            key[encrypted] = orig

    error_chars = []
    for char in text:
        if char not in key:
            if char.isalpha():
                # a character was found in the message that was not in the key
                # so this decoder key was used with the wrong message?
                # just store to report error later and write out the original
                error_chars.append(char)

            out.append(char)
        else:
            out.append(key[char])

    if error_chars:
        print(f"WARNING The following letters did not have substitutions in the decoder key: {error_chars}")

    return "".join(out)


def decrypt(text: str, decoder: str) -> dict:
    return encryption(text, decoder, task="decrypt")


def encrypt(text: str, decoder: dict) -> str:
    return encryption(text, decoder, task="encrypt")


def create_decoder(text: str) -> dict:
    counter = Counter()
    counter.update(text)

    reversed_counts = {}
    for letter, count in counter.items():
        if count not in reversed_counts:
            reversed_counts[count] = []
        reversed_counts[count].append(letter)

    counts = list(reversed_counts.keys())
    counts.sort(reverse=True)

    # decoder format is original, count, substition
    decoder = {}

    pointer = 0
    for count in counts:
        letters = reversed_counts[count]
        letters.sort()
        for letter in letters:
            if not letter.isalpha():
                continue
            decoder[letter] = (count, string.ascii_lowercase[pointer])
            pointer += 1

    return decoder


def save_file(text: str, filename: str):
    with open(filename, 'w') as f:
        f.write(text)


def load_file(filename: str) -> str:
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        raise RuntimeError(f"{filename} does not exist")


def parse_decoder(text: str) -> dict:
    decoder = {}
    substitutions = set()

    lines = text.split("\n")
    for n, line in enumerate(lines):
        try:
            orig, count, substitution = line.split(",")
        except ValueError:
            raise RuntimeError(f"Incorrect formatting on decoder file line {n + 1}")

        if orig in decoder:
            raise RuntimeError(f"Original letter {orig} is mapped to a substitution more than once!")

        if substitution in substitutions:
            raise RuntimeError(f"Substitution letter {substitution} is mapped to an original letter more than once!")

        substitutions.add(substitution)
        decoder[orig] = (int(count), substitution)

    return decoder


def decoder_to_string(decoder: dict) -> str:
    out = []
    for orig, tup in decoder.items():
        count, sub = tup
        out.append(",".join([orig, str(count), sub]))

    return "\n".join(out)


def run(action, input_filename, output_filename, decoder_filename):

    text = load_file(input_filename)

    if action == 'decrypt':
        decoder = load_file(decoder_filename)
        decoder = parse_decoder(decoder)
        output = decrypt(text, decoder)
    else:
        decoder = create_decoder(text)
        output = encrypt(text, decoder)
        decoder_string = decoder_to_string(decoder)

        save_file(decoder_string, decoder_filename)

    save_file(output, output_filename)


def main():
    # command line format:
    # problem.py encrypt original.txt encrypted.txt decoder.txt
    # OR
    # problem.py decrypt encrypted.txt decrypted.txt decoder.txt
    parser = argparse.ArgumentParser()

    # spec is for positional arguments
    parser.add_argument('action', choices=['encrypt', 'decrypt'])
    parser.add_argument('input_filename')
    parser.add_argument('output_filename')
    parser.add_argument('decoder_filename', default='decoder.txt')
    args = parser.parse_args()

    try:
        run(args.action, args.input_filename, args.output_filename, args.decoder_filename)
    except RuntimeError as e:
        print(str(e))
        return


if __name__ == "__main__":
    main()
