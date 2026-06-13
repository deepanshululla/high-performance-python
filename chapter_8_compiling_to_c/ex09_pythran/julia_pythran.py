# Pythran source: compiled ahead-of-time by the `pythran` CLI into a native .so.
# The single magic line below is the entire annotation burden -- it tells Pythran the
# argument types so it can generate a specialized C++ kernel (and it always releases the
# GIL, and may auto-vectorize with SIMD).
#pythran export calc(int, complex128[:], complex128[:])
import numpy as np


def calc(maxiter, zs, cs):
    """The same expanded-math Julia loop, as plain numpy-flavoured Python."""
    output = np.empty(len(zs), dtype=np.int32)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n
    return output
