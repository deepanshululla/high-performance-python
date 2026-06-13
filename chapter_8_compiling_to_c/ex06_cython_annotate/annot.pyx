# cython: language_level=3
"""Two versions of the Julia inner loop, for `cython -a` to annotate side by side.

`plain` is the unannotated Python (every line calls into the VM); `typed` adds the C
scalar types and expanded math. Running `cython -a annot.pyx` shades each line by how
much it talks to the Python virtual machine -- ex06 parses those shading scores instead
of reading the colours by eye.
"""


def plain(maxiter, zs, cs):
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


def typed(int maxiter, zs, cs):
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
