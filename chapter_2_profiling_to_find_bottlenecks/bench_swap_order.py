"""Does swapping the order of the compound `while` condition matter?

Original:  while abs(z) < 2 and n < maxiter:     # expensive test first
Swapped:   while n < maxiter and abs(z) < 2:     # cheap test first

Builds the 1000x1000 grid once, then times both versions repeatedly and
reports the best (min) of several runs for each.
"""
import time
import timeit

X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193


def original(maxiter, zs, cs):
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while abs(z) < 2 and n < maxiter:      # expensive first
            z = z * z + c
            n += 1
        output[i] = n
    return output


def swapped(maxiter, zs, cs):
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while n < maxiter and abs(z) < 2:      # cheap first
            z = z * z + c
            n += 1
        output[i] = n
    return output


def build_grid(desired_width=1000):
    x_step = (X2 - X1) / desired_width
    y_step = (Y1 - Y2) / desired_width
    x, y = [], []
    ycoord = Y2
    while ycoord > Y1:
        y.append(ycoord)
        ycoord += y_step
    xcoord = X1
    while xcoord < X2:
        x.append(xcoord)
        xcoord += x_step
    zs, cs = [], []
    for ycoord in y:
        for xcoord in x:
            zs.append(complex(xcoord, ycoord))
            cs.append(complex(C_REAL, C_IMAG))
    return zs, cs


if __name__ == "__main__":
    REPEAT, MAXITER = 5, 300
    zs, cs = build_grid(1000)
    assert sum(original(MAXITER, zs, cs)) == 33219980
    assert sum(swapped(MAXITER, zs, cs)) == 33219980  # both give identical results

    orig = timeit.repeat(lambda: original(MAXITER, zs, cs), number=1, repeat=REPEAT)
    swap = timeit.repeat(lambda: swapped(MAXITER, zs, cs), number=1, repeat=REPEAT)

    bo, bs = min(orig), min(swap)
    print(f"original (abs first):  best {bo:.4f}s   all {[f'{t:.3f}' for t in orig]}")
    print(f"swapped  (n   first):  best {bs:.4f}s   all {[f'{t:.3f}' for t in swap]}")
    delta = (bo - bs) / bo * 100
    faster = "swapped" if bs < bo else "original"
    print(f"=> {faster} is faster by {abs(delta):.2f}%  (best-of-{REPEAT})")
