# cython: language_level=3
# distutils: language = c
"""Cython + numpy-memoryview Julia loop, serial and OpenMP-parallel (Examples 8-9, 8-10).

Two functions over the SAME typed-memoryview inputs:

  serial  - one thread; expanded math; the Table 8-2 "Cython" row (Example 8-9)
  omp     - prange + nogil + schedule="guided"; the "Cython and OpenMP" row (Ex 8-10)

The arguments are `double complex[:]` memoryviews, not Python lists: indexing them is a
direct memory offset in C, with no trip back into the VM. That is the difference ex02
could not reach with lists. Once the dereference is C-level, releasing the GIL and
fanning the outer loop across cores with prange is nearly free.
"""
import numpy as np
cimport cython
from cython.parallel import prange


@cython.boundscheck(False)
@cython.wraparound(False)
def serial(int maxiter, double complex[:] zs, double complex[:] cs):
    """Single-threaded memoryview loop with expanded math. Returns an int32 array."""
    cdef unsigned int i, n, length = zs.shape[0]
    cdef double complex z, c
    cdef int[:] output = np.empty(length, dtype=np.int32)
    for i in range(length):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n
    return np.asarray(output)


@cython.boundscheck(False)
@cython.wraparound(False)
def omp(int maxiter, double complex[:] zs, double complex[:] cs):
    """Same loop, but the outer range is a prange under nogil: OpenMP spreads pixels
    across cores. 'guided' hands out shrinking chunks so the cheap and the expensive
    regions of the fractal stay balanced."""
    cdef unsigned int i, length = zs.shape[0]
    cdef double complex z, c
    cdef int[:] output = np.empty(length, dtype=np.int32)
    with nogil:
        for i in prange(length, schedule="guided"):
            z = zs[i]
            c = cs[i]
            output[i] = 0
            while output[i] < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
                z = z * z + c
                output[i] += 1
    return np.asarray(output)
