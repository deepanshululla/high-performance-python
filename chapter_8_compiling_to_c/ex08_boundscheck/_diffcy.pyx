# cython: language_level=3
"""A Cython 2D-diffusion kernel that indexes a memoryview in its INNER loop.

ex02 showed that disabling bounds checks bought nothing on the Julia loop -- because its
inner loop only touched C scalars; the list dereference was in the cheap outer loop. This
kernel is the opposite: every inner iteration reads five neighbours and writes one cell,
so memoryview indexing IS the hot path. That's where the chapter's tip applies:

  "Try disabling bounds checking and wraparound checking if your CPU-bound code is in a
   loop that is dereferencing items frequently."

`checked` runs with Cython's defaults (bounds + wraparound checks on); `unchecked` turns
both off. Same arithmetic, same result -- the only difference is the per-access guard.
"""
cimport cython


def checked(double[:, :] grid, double[:, :] out, double D, double dt):
    """Default Cython: every grid[i,j] access is bounds- and wraparound-checked."""
    cdef Py_ssize_t i, j, n = grid.shape[0], m = grid.shape[1]
    cdef double lap
    for i in range(1, n - 1):
        for j in range(1, m - 1):
            lap = (grid[i + 1, j] + grid[i - 1, j] + grid[i, j + 1] + grid[i, j - 1]
                   - 4 * grid[i, j])
            out[i, j] = grid[i, j] + D * dt * lap


@cython.boundscheck(False)
@cython.wraparound(False)
def unchecked(double[:, :] grid, double[:, :] out, double D, double dt):
    """Same loop with both guards removed: each access is a bare pointer offset."""
    cdef Py_ssize_t i, j, n = grid.shape[0], m = grid.shape[1]
    cdef double lap
    for i in range(1, n - 1):
        for j in range(1, m - 1):
            lap = (grid[i + 1, j] + grid[i - 1, j] + grid[i, j + 1] + grid[i, j - 1]
                   - 4 * grid[i, j])
            out[i, j] = grid[i, j] + D * dt * lap
