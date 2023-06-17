from enum import Enum


class Operator(Enum):
    EXCLUDE = "!"
    UNKNOWN_POSITION = "?"
    CLEAR = "*"
    MASK = "."

    @staticmethod
    def is_exclude(pattern):
        return pattern[0] == Operator.EXCLUDE.value

    @staticmethod
    def is_clear(pattern):
        return pattern[0] == Operator.CLEAR.value

    @staticmethod
    def is_unknown_position(pattern):
        return pattern[0] == Operator.UNKNOWN_POSITION.value
