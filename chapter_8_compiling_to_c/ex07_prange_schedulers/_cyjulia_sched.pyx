# cython: language_level=3
"""The Julia OpenMP loop compiled with three prange schedules (Example 8-10 territory).

Identical bodies; only the `schedule=` differs. The chapter explains why this matters:
Julia work is wildly uneven across the grid (points that escape immediately cost almost
nothing; points deep in the set run the full maxiter), so how OpenMP hands pixels to
threads decides how long the slowest thread runs.

  static  - split the range into N equal contiguous blocks up front. If one block lands
            on the expensive interior of the fractal, that thread runs long while others
            finish early and idle.
  dynamic - hand out small fixed chunks on demand; threads that finish grab more.
  guided  - like dynamic but chunks start large and shrink, trading a little less
            scheduling overhead for good balance on the long tail.
"""
import numpy as np
cimport cython
from cython.parallel import prange


@cython.boundscheck(False)
@cython.wraparound(False)
cdef int[:] _run(int maxiter, double complex[:] zs, double complex[:] cs, str sched):
    cdef unsigned int i, length = zs.shape[0]
    cdef double complex z, c
    cdef int[:] output = np.empty(length, dtype=np.int32)
    if sched == "static":
        with nogil:
            for i in prange(length, schedule="static"):
                z = zs[i]; c = cs[i]; output[i] = 0
                while output[i] < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
                    z = z * z + c; output[i] += 1
    elif sched == "dynamic":
        with nogil:
            for i in prange(length, schedule="dynamic"):
                z = zs[i]; c = cs[i]; output[i] = 0
                while output[i] < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
                    z = z * z + c; output[i] += 1
    else:  # guided
        with nogil:
            for i in prange(length, schedule="guided"):
                z = zs[i]; c = cs[i]; output[i] = 0
                while output[i] < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
                    z = z * z + c; output[i] += 1
    return output


def static(int maxiter, double complex[:] zs, double complex[:] cs):
    return np.asarray(_run(maxiter, zs, cs, "static"))


def dynamic(int maxiter, double complex[:] zs, double complex[:] cs):
    return np.asarray(_run(maxiter, zs, cs, "dynamic"))


def guided(int maxiter, double complex[:] zs, double complex[:] cs):
    return np.asarray(_run(maxiter, zs, cs, "guided"))
