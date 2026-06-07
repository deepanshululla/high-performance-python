"""Chapter 4 - Exercise 9: the integer-hash identity.

Task: show that 5 and 501 collide in a tiny dict but not a large one.

Takeaway: hash(int) is (mostly) the integer itself. For an infinite table the
mask is infinite, so distinct ints never share all bits -> ideal hash. A finite
table's mask is what reintroduces collisions.

Run: .venv/bin/python chapter_4/ex09_int_hash/ex09_int_hash.py
"""


def main():
    for size in (8, 1024):
        mask = size - 1
        a, b = 5 & mask, 501 & mask
        print(f"size {size:>5} (mask {mask:#013b}): 5->{a}, 501->{b}  "
              f"{'COLLIDE' if a == b else 'ok'}")

    print(f"\nhash(5)={hash(5)}, hash(501)={hash(501)}  (int hash == itself in range)")
    print(f"edge case: hash(-1)={hash(-1)} (CPython maps -1 to -2)")


if __name__ == "__main__":
    main()
