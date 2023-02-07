'''
Given a list of integers, return the smallest integer greater than zero that does not appear in the list.

Example 1: [1, 3, 6, 4, 1, 2]
Output: 5

Example 2: [-1, -3]
Output: 1
'''


def solution(supplied: list) -> int:

    supplied_set = set(supplied)
    output_set = {1}

    for val in supplied:
        if val <= 0:
            continue
        output_set.add(val+1)

    output_set -= supplied_set
    return min(output_set)


test = [1, 3, 6, 4, 1, 2]
print(solution(test))
