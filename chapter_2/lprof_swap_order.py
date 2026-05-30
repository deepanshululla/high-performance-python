"""Line-profile the two condition orderings, one call each.

Run with autoprofiling:
    uv run kernprof -l -v -p chapter_2/lprof_swap_order.py chapter_2/lprof_swap_order.py

Compare the `while` line in `original` vs `swapped`: the Hits column shows how
many times each ordering evaluated the loop condition, and Time/% Time shows
whether putting the cheap test first changed the cost.
"""
X1, X2, Y1, Y2 = -1.8, 1.8, -1.8, 1.8
C_REAL, C_IMAG = -0.62772, -0.42193


def original(maxiter, zs, cs):
    output = [0] * len(zs)
    for i in range(len(zs)):
        n = 0
        z = zs[i]
        c = cs[i]
        while abs(z) < 2 and n < maxiter:      # expensive test first
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
        while n < maxiter and abs(z) < 2:      # cheap test first
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
    zs, cs = build_grid(1000)
    assert sum(original(300, zs, cs)) == 33219980
    assert sum(swapped(300, zs, cs)) == 33219980
    print("both produced identical results (checksum 33219980)")
