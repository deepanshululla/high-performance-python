"""Chapter 5 - Exercise 8: convert an eager function into a lazy pipeline.

Task: this function loads a whole file, strips non-comment lines, uppercases
them, and returns matches. Rewrite it as a generator pipeline that streams line
by line and supports early termination via islice.

Takeaway: each stage is a generator expression chained to the next; one line
flows through at a time, the file is never fully read, and islice lets callers
stop early. Trade-off: the result is single-pass (can't iterate twice / index).

Run: .venv/bin/python chapter_5/ex08_eager_to_lazy.py
"""
import pathlib
import sys
import tempfile
from itertools import islice

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402


def find_matches_eager(path, term):
    lines = open(path).read().splitlines()
    cleaned = [line.strip() for line in lines if not line.startswith("#")]
    upper = [line.upper() for line in cleaned]
    return [line for line in upper if term in line]


def find_matches_lazy(path, term):
    with open(path) as fd:
        stripped = (line.strip() for line in fd if not line.startswith("#"))
        upper = (line.upper() for line in stripped)
        yield from (line for line in upper if term in line)


def main():
    sample = "\n".join(["# comment", "error here", "all good", "ERROR again", "fine", "an error too"])
    with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as f:
        f.write(sample)
        path = f.name

    print("eager full result:", find_matches_eager(path, "ERROR"))
    print("lazy first 1:     ", list(islice(find_matches_lazy(path, "ERROR"), 1)))
    print("(lazy reads only enough of the file to yield what's pulled)")

    # Build a big file: 1,000,000 lines, one ERROR near the top.
    big = pathlib.Path(tempfile.gettempdir()) / "ch5_ex08_big.log"
    with open(big, "w") as f:
        f.write("ERROR right at the top\n")
        for i in range(1_000_000):
            f.write(f"line {i} all good\n")

    eager_first = lambda: find_matches_eager(str(big), "ERROR")[0]            # loads whole file
    lazy_first = lambda: next(find_matches_lazy(str(big), "ERROR"))           # stops at first hit
    print("\nFind the FIRST match in a 1,000,001-line file:")
    print(f"  eager (load all): {time_s(eager_first, number=1, repeat=3) * 1e3:7.1f} ms   peak {human(peak_bytes(eager_first))}")
    print(f"  lazy  (stop early): {time_s(lazy_first, number=1, repeat=3) * 1e3:7.1f} ms   peak {human(peak_bytes(lazy_first))}")
    print("  -> lazy reads ~1 line and allocates almost nothing; eager reads + stores all 1M")
    big.unlink()


if __name__ == "__main__":
    main()
