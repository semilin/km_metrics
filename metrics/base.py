## NOTE: Combos can now be inputs to functions. For functions where
## you want this, be careful to ensure that all the code can handle
## combos. Otherwise, there is a "splittable" field in the METRIC_LIST
## which, if True, has the metric processor automatically split the
## combos for the given metric, removing the need for manually
## handling combos. Set this to False for metrics which need to handle
## combos themselves.

from math import sqrt
from enum import Enum
from metric import *
from keyboard import *
import itertools

Direction = Enum("Direction", ["INWARD", "OUTWARD", "NONE"])

def bistroke_direction(a, b):
    "Direction of simple bistroke, not allowing combos."
    if a.finger == b.finger or a.finger.hand() != b.finger.hand():
        return Direction.NONE
    if a.finger.kind().value < b.finger.kind().value:
        return Direction.INWARD
    return Direction.OUTWARD

def direction(a, b):
    l = split(bistroke_direction, a, b)
    if len(set(l)) == 1:
        return l[0]
    else:
        return Direction.NONE

def x_distance(a, b):
    return abs(a.x - b.x)

def y_distance(a, b):
    return abs(a.y - b.y)

def distance(a, b):
    return sqrt(x_distance(a, b) ** 2 +
                y_distance(a, b) ** 2)

def different_hands(a, b):
    return False not in split(lambda a, b: a.finger.hand() != b.finger.hand(), a, b)

def same_hands(a, b):
    return False not in split(lambda a, b: a.finger.hand() == b.finger.hand(), a, b)

def same_rows(a, b):
    return False not in split(lambda a, b: a.pos.row == b.pos.row, a, b)

def is_sfr(a, b):
    return a == b

def is_sfb(a, b):
    return (not is_sfr(a, b)
            and a.finger == b.finger)

def has_same_finger(a, b):
    """Returns true if any of the combo splits contains two positions pressed with the same finger."""
    return True in split(lambda a, b : a.finger == b.finger, a, b)

def is_lsb(a, b):
    return (a.finger.hand() == b.finger.hand()
            and abs(a.finger.kind().value - b.finger.kind().value) == 1
            and x_distance(a, b) >= 2)

def is_alternate(a, b, c):
    return (different_hands(a, b)
            and same_hands(a, c))

def is_roll(a, b, c):
    return (different_hands(a, c)
            and not has_same_finger(a, b)
            and not has_same_finger(b, c))

def is_redirect(a, b, c):
    return (same_hands(a, b) and same_hands(b, c)
            and not has_same_finger(a, b)
            and not has_same_finger(b, c)
            and direction(a, b) != direction(b, c))

def is_same_row_roll(a, b, c):
    return (is_roll(a, b, c)
            and same_rows(a, b)
            and same_rows(b, c))

METRIC_LIST = [
    Metric("Same-finger Repeats", "sfr", NgramType.BIGRAM, is_sfr, 1, True),
    Metric("Same-finger Bigrams", "sfb", NgramType.BIGRAM, is_sfb, 1, True),
    Metric("Same-finger Skipgrams", "sfs", NgramType.SKIPGRAM, is_sfb, 1, True),
    Metric("Same-finger Bigram Distance", "sfb-dist", NgramType.BIGRAM, is_sfb, distance, True),
    Metric("Same-finger Skipgram Distance", "sfs-dist", NgramType.SKIPGRAM, is_sfb, distance, True),
    Metric("Lateral Stretch Bigrams", "lsb", NgramType.BIGRAM, is_lsb, 1, True),
    Metric("Lateral Stretch Bigram Distance", "lsb-dist", NgramType.BIGRAM, is_lsb, x_distance, True),
    Metric("Alternates", "alt", NgramType.TRIGRAM, is_alternate, 1, False),
    Metric("Rolls", "roll", NgramType.TRIGRAM, is_roll, 1, False),
    Metric("Same-row Rolls", "sr-roll", NgramType.TRIGRAM, is_same_row_roll, 1, False),
    Metric("Redirects", "redir", NgramType.TRIGRAM, is_redirect, 1, False)
]
