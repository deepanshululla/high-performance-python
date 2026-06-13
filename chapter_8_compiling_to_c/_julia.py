"""Shared Julia-set problem definition for every Chapter 8 exercise.

The whole chapter optimizes ONE workload — the CPU-bound Julia-set generator from
Chapter 2 — with progressively heavier compilers. Keeping the problem in a single
module means ex01..ex04 all time the *same* arithmetic on the *same* inputs, so the
numbers line up into the book's Table 8-1 / Table 8-2.

Book parameters (Example 8-1): a 1000x1000 grid, maxiter=300, with the constant
c = -0.62772 - 0.42193j over the square [-1.8, 1.8]^2. The pure-Python run is ~5-6s
on the authors' laptop; everything compiled drops to well under a second.
"""
import numpy as np

# Canonical constants from the book's julia1.py.
X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193
DEFAULT_WIDTH = 1000
DEFAULT_MAXITER = 300


def build_inputs(width=DEFAULT_WIDTH):
    """Return (zs, cs) as plain Python lists of complex — the list-based inputs.

    `zs` is the grid of starting coordinates; `cs` is the same Julia constant
    repeated for every pixel. This mirrors calc_pure_python() in the book.
    """
    x_step = (X2 - X1) / width
    y_step = (Y1 - Y2) / width
    x = [X1 + i * x_step for i in range(width)]
    y = [Y2 + i * y_step for i in range(width)]

    zs, cs = [], []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(C_REAL, C_IMAG))
    return zs, cs


def build_inputs_numpy(width=DEFAULT_WIDTH):
    """Return (zs, cs) as contiguous complex128 numpy arrays — the array inputs.

    Same coordinates as build_inputs(), but laid out for memoryview/Numba access.
    """
    zs, cs = build_inputs(width)
    return np.asarray(zs, dtype=np.complex128), np.asarray(cs, dtype=np.complex128)


def expected_checksum(width=DEFAULT_WIDTH, maxiter=DEFAULT_MAXITER):
    """The book's correctness anchor: sum(output) == 33219980 for the 1000-wide grid.

    Every exercise asserts against this so a faster variant that quietly computes the
    wrong thing is caught immediately. (The value only holds for width=1000/maxiter=300.)
    """
    if width == DEFAULT_WIDTH and maxiter == DEFAULT_MAXITER:
        return 33219980
    return None
