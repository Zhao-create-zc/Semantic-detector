"""Adapted from BinaryInferno entropybound.py

Original: https://github.com/BinaryInferno/BinaryInferno
Copyright (C) 2023 Jared Chandler (jared.chandler@tufts.edu)
License: GNU General Public License v3.0 (GPLv3)

Adapted: Pure entropy function H(), stripped of BI-specific
dependencies (sumeng, Sigma, deconflict, Weights, print).
"""

# Original copyright and license notice retained above.
# This file is a modified copy — not the original.

from collections import Counter
import math


def H(xs):
    """Calculate Shannon entropy of a sequence.

    Adapted from BinaryInferno entropybound.py H() function.
    Returns entropy in bits (>= 0).

    Args:
        xs: Iterable of hashable values

    Returns:
        float: Shannon entropy in bits
    """
    xs_str = [str(x) for x in xs]
    n = len(xs_str)
    if n == 0:
        return 0.0

    qty = Counter(xs_str)
    tot = 0.0
    for item in qty:
        v = qty[item]
        p = v / n
        assert p <= 1.0
        if p > 0:
            tot += p * math.log(p, 2)
    return abs(-tot)
