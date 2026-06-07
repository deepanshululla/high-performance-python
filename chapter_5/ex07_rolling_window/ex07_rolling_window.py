"""Chapter 5 - Exercise 7: rolling window, tuple-rebuild vs deque (Example 5-7).

Task: implement a sliding window two ways and contrast O(n)-per-slide tuple
rebuilding with O(1) deque append/popleft.

Takeaway: `window[1:] + (item,)` allocates a fresh tuple every step (O(n)). A
deque gives O(1) append-right + auto popleft (maxlen). The catch: a deque is
mutated in place, so you must copy to a tuple before yielding or every prior
window mutates under the caller -- which claws back some of the savings.

Run: .venv/bin/python chapter_5/ex07_rolling_window/ex07_rolling_window.py
"""
import pathlib
import sys
from collections import deque
from itertools import islice

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import time_s  # noqa: E402


def groupby_window_tuple(data, window_size=3):
    it = iter(data)
    window = tuple(islice(it, window_size))
    yield window
    for item in it:
        window = window[1:] + (item,)          # O(window_size) per slide
        yield window


def groupby_window_deque(data, window_size=3):
    """Deque, but copies to a tuple each yield so the caller gets a stable snapshot."""
    it = iter(data)
    window = deque(islice(it, window_size), maxlen=window_size)
    yield tuple(window)
    for item in it:
        window.append(item)                    # O(1); maxlen auto-drops the left
        yield tuple(window)                    # but this copy is O(window) again!


def groupby_window_deque_inplace(data, window_size=3):
    """Deque yielding the LIVE window -- O(1) per slide, no copy.

    Caveat (the book's warning): the caller must consume each window immediately
    and must NOT retain it, because every yield hands back the same mutating object.
    """
    it = iter(data)
    window = deque(islice(it, window_size), maxlen=window_size)
    yield window
    for item in it:
        window.append(item)                    # O(1), and we yield it as-is
        yield window


def main():
    data = list(range(8))
    print("tuple-rebuild:", list(groupby_window_tuple(data, 3)))
    print("deque-based  :", list(groupby_window_deque(data, 3)))
    assert list(groupby_window_tuple(data, 3)) == list(groupby_window_deque(data, 3))
    print("both produce identical windows")

    # Time: counterintuitive result -- the deque only wins if you DON'T copy.
    # tuple-rebuild and deque+tuple(copy) are BOTH O(window) per slide; only the
    # in-place deque (no copy) is truly O(1) per slide.
    stream = list(range(50_000))
    print("\nTime to slide a window across 50,000 items (sum window lengths):")
    print(f"  {'window':>7} {'tuple-rebuild':>14} {'deque+copy':>12} {'deque in-place':>16}")
    for w in (100, 1_000, 5_000):
        t_tup = time_s(lambda: sum(len(x) for x in groupby_window_tuple(stream, w)), number=1, repeat=3)
        t_cpy = time_s(lambda: sum(len(x) for x in groupby_window_deque(stream, w)), number=1, repeat=3)
        t_inp = time_s(lambda: sum(len(x) for x in groupby_window_deque_inplace(stream, w)), number=1, repeat=3)
        print(f"  {w:>7} {t_tup * 1e3:11.1f} ms {t_cpy * 1e3:9.1f} ms {t_inp * 1e3:13.1f} ms")
    print("\nLesson (matches the book's caveat): copying to a tuple each yield is")
    print("O(window) and ERASES the deque's advantage -- deque+copy is no faster than")
    print("tuple-rebuild. The deque only pays off (flat, O(1)/slide) if the consumer")
    print("reads the live window in place and never retains it.")
    print("Memory: all variants hold exactly one window of state.")


if __name__ == "__main__":
    main()
