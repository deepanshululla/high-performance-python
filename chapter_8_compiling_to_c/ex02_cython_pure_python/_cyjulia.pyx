# cython: language_level=3
"""Cython pure-Python ladder for the Julia inner loop (Examples 8-3, 8-7, 8-8).

Four rungs, each a separate compiled function, so ex02 can time the exact jump each
source change buys:

  v0_plain     - the unmodified Python loop, merely run through Cython (Example 8-3)
  v1_typed     - cdef the loop scalars to C types, abs() escape test (Example 8-7)
  v2_expanded  - same types, abs() replaced by re*re+im*im < 4 (Example 8-8)
  v3_nobounds  - v2 with boundscheck/wraparound disabled (the book's final tweak)

The `zs`/`cs` arguments stay Python lists on purpose: this is the "no numpy" column
of Table 8-1. List dereferences still call into the VM (that's what ex03 fixes with
memoryviews), so v3's bounds-check removal is expected to do ~nothing here.
"""
cimport cython


def v0_plain(maxiter, zs, cs):
    """Unannotated Python, compiled. Speedup comes only from skipping the interpreter."""
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and abs(z) < 2:
            z = z * z + c
            n += 1
        output[i] = n
    return output


def v1_typed(int maxiter, zs, cs):
    """C types for the hot scalars; abs() escape test. Pushes z/n updates to C."""
    cdef unsigned int i, n
    cdef double complex z, c
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and abs(z) < 2:
            z = z * z + c
            n += 1
        output[i] = n
    return output


def v2_expanded(int maxiter, zs, cs):
    """Typed + strength reduction: abs(z) < 2 -> re*re + im*im < 4 (drops the sqrt)."""
    cdef unsigned int i, n
    cdef double complex z, c
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n
    return output


@cython.boundscheck(False)
@cython.wraparound(False)
def v3_nobounds(int maxiter, zs, cs):
    """v2 with bounds/wraparound checks off. On Python lists this buys ~nothing --
    the dereference still goes through the VM, and the checks were in the cheap outer
    loop anyway. Included to show the book's caveat is true, not just stated."""
    cdef unsigned int i, n
    cdef double complex z, c
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and (z.real * z.real + z.imag * z.imag) < 4:
            z = z * z + c
            n += 1
        output[i] = n
    return output
