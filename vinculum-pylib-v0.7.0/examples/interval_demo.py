"""Uncertain inputs remain uncertain after an exact calculation."""
from vinculum import NumericRange
from vinculum.symbolic import interval_calculate

if __name__ == "__main__":
    result = interval_calculate("distance / speed", {
        "distance": NumericRange(90, 110),
        "speed": NumericRange(9, 11),
    })
    # The caller defines compatible units; no hidden unit inference is performed.
    print(result)
