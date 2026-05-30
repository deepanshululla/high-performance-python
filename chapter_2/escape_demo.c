/* Tiny C versions of the Julia inner-loop operations, to compare the resulting
 * machine assembly against CPython's bytecode for the same work.
 *
 *   clang -O2 -S escape_demo.c -o escape_demo.s     # generate ARM64 assembly
 */

/* Python `n += 1` is 5 bytecode ops; in C it is one machine instruction. */
int inc(int n) {
    return n + 1;
}

/* The inner step `z = z*z + c` on a complex number, done with real doubles.
 * Compiles to native floating-point instructions — no interpreter, no boxing. */
void z_squared_plus_c(double *zr, double *zi, double cr, double ci) {
    double r = *zr, i = *zi;
    *zr = r * r - i * i + cr;   /* real part */
    *zi = 2.0 * r * i + ci;     /* imag part */
}
