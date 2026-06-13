/* cdiffusion.c -- the diffusion kernel, identical to ex05's evolve (Example 8-18).
 * Grid fixed at 512x512 so the signature stays simple. */
#include "cdiffusion.h"

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
