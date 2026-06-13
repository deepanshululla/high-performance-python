/* diffusion.c -- the book's Example 8-18: one step of the 2D heat equation.
 *
 * The grid size is fixed at 512x512 to keep the signature simple (an arbitrary size
 * would need double-pointer args plus explicit dimensions). Borders are left untouched,
 * so callers should pass an `out` whose borders already hold the values they want.
 *
 * Build a shared library:
 *     cc -O3 -std=gnu11 -shared -o diffusion.so diffusion.c
 */
void evolve(double in[][512], double out[][512], double D, double dt) {
    int i, j;
    double laplacian;
    for (i = 1; i < 511; i++) {
        for (j = 1; j < 511; j++) {
            laplacian = in[i+1][j] + in[i-1][j] + in[i][j+1] + in[i][j-1]
                        - 4 * in[i][j];
            out[i][j] = in[i][j] + D * dt * laplacian;
        }
    }
}
