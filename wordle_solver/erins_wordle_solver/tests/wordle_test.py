import unittest
from erins_wordle_solver.solve_wordle import check_pattern


class MyTestCase(unittest.TestCase):

    def test_pattern_check(self):

        word_len = 5
        good_patterns = [".....a", ".....", "abcde", "a.....", "!abc", "?abc", "?a1b2c3",  "?a1bc", "?ab2c3", "?a12b100"]

        for p in good_patterns:
            print("Testing good:", p)
            res = check_pattern(p, word_len)
            self.assertEqual(res, True)

        bad_patterns = ["abcdef", "......", "?.asd", ".?abc", "!!!!!", ".999.", "01754", "=abcd", "?!?!?!"]
        for p in bad_patterns:
            print("Testing bad:", p)
            res = check_pattern(p, word_len, show_help=False)
            self.assertEqual(res, False)


if __name__ == '__main__':
    unittest.main()
