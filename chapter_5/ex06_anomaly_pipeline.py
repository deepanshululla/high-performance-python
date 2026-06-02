"""Chapter 5 - Exercise 6: a lazy anomaly-detection pipeline (Examples 5-3..5-6).

Task: wire read -> group-by-day -> filter-anomalous -> islice(5) so the full
(here: infinite/fake) dataset is never loaded. Print the first 5 anomalous days.

Takeaway: islice(..., 5) makes the chain finish: each next() propagates back to
the reader, which generates exactly enough data to surface 5 anomalies, then
stops. Nothing downstream runs until pulled -- lazy evaluation.

NOTE: the book uses scipy.stats.normaltest. This project has numpy but not
scipy, so is_normal() below is a simplified stand-in: a day is "anomalous" if it
contains a value far outside the normal(0,1) range. The point of the exercise is
the generator pipeline, not the statistical test.

Run: .venv/bin/python chapter_5/ex06_anomaly_pipeline.py
"""
import pathlib
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import count, groupby, filterfalse, islice
from operator import attrgetter
from random import normalvariate, randint, seed

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from perf import peak_bytes, time_s, human  # noqa: E402


@dataclass
class Datum:
    date: datetime
    value: float


def read_fake_data(filename):
    """Lazily emit one Datum per simulated second; inject a spike ~weekly."""
    for ts in count():
        if randint(0, 7 * 60 * 60 * 24 - 1) == 1:
            value = 100.0                       # anomaly
        else:
            value = normalvariate(0, 1)
        yield Datum(datetime.fromtimestamp(ts), value)


def groupby_day(iterable):
    key = lambda row: row.date.day
    for _, group in groupby(iterable, key):     # groups CONSECUTIVE equal keys
        yield list(group)


def is_normal(data, threshold=10.0):
    """Stand-in for scipy.stats.normaltest: normal(0,1) values stay well within
    +/-threshold; the injected 100.0 spikes do not."""
    return max(abs(v) for v in map(attrgetter("value"), data)) < threshold


def filter_anomalous_groups(data):
    yield from filterfalse(is_normal, data)


def filter_anomalous_data(data):
    yield from filter_anomalous_groups(groupby_day(data))


def first_n_anomaly_ranges(n):
    """Pull n anomalous days but retain only their (start, end) dates -- NOT the
    full day of data. This is what keeps memory flat: each ~86,400-point day is
    materialized transiently, scored, then discarded."""
    out = []
    for day in islice(filter_anomalous_data(read_fake_data("ignored")), n):
        out.append((day[0].date, day[-1].date))
    return out


def main():
    seed(0)
    for start, end in first_n_anomaly_ranges(5):
        print(f"Anomaly from {start} - {end}")

    # Because we keep only date ranges (not the day lists), peak memory is flat:
    # the pipeline never holds more than ~one day in flight, no matter how deep we go.
    print("\nTime + memory by number of anomalies pulled (peak = tracemalloc):")
    for n in (5, 10, 20):
        seed(0)
        t = time_s(lambda: first_n_anomaly_ranges(n), number=1, repeat=2)
        seed(0)
        m = peak_bytes(lambda: first_n_anomaly_ranges(n))
        print(f"  first {n:>2}: {t * 1e3:7.1f} ms   peak {human(m)}")
    print("  -> peak memory is ~FLAT (one day in flight); only TIME grows with n.")
    print("  islice stops the whole chain after the n-th anomaly -- lazy evaluation.")
    print("  (Retaining the full day lists instead would make memory grow ~n*day.)")


if __name__ == "__main__":
    main()
