! diffusion.f90 -- the book's Example 8-22: 2D diffusion as a Fortran subroutine.
!
! The !f2py annotations are the whole trick. They tell f2py how each argument is used so
! the generated Python interface is clean: `intent(in)` for read-only inputs,
! `intent(inplace)` to write next_grid in place, and `intent(hide)` for the grid sizes N
! and M -- Fortran needs them explicitly, but Python already knows the array shape, so
! f2py fills them in and hides them from the final signature: evolve(grid, next_grid, D, dt).
SUBROUTINE evolve(grid, next_grid, D, dt, N, M)
    !f2py threadsafe
    !f2py intent(in) grid
    !f2py intent(inplace) next_grid
    !f2py intent(in) D
    !f2py intent(in) dt
    !f2py intent(hide) N
    !f2py intent(hide) M
    INTEGER :: N, M
    DOUBLE PRECISION, DIMENSION(N,M) :: grid, next_grid
    DOUBLE PRECISION, DIMENSION(N-2, M-2) :: laplacian
    DOUBLE PRECISION :: D, dt

    laplacian = grid(3:N, 2:M-1) + grid(1:N-2, 2:M-1) + &
                grid(2:N-1, 3:M) + grid(2:N-1, 1:M-2) - 4 * grid(2:N-1, 2:M-1)
    next_grid(2:N-1, 2:M-1) = grid(2:N-1, 2:M-1) + D * dt * laplacian
END SUBROUTINE evolve
