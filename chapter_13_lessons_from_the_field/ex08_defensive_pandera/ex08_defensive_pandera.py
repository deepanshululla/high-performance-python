"""ex08 — defensive code: a Pandera schema catches the bad data that quietly corrupts results.

James Poynter's lesson from cyber-reinsurance: data is just another input to your program, and
deserves the same defensive treatment as any other — validation, assertions, boundary checks.
The danger isn't the bad row that crashes; it's the bad row that *doesn't* — the missing value
encoded as a sentinel, the negative premium from a data-entry slip, the out-of-range score —
which sails through the pipeline and silently poisons the number a business decision rests on.
"Writing code to guard against data quality issues takes time up front, but the return on
investment is realized relatively quickly."

We build a tiny insurance pipeline: a premium-weighted average risk score across a portfolio.
On clean data it's correct. Then we inject realistic, *non-crashing* impurities — risk scores
of -1 (a CSV's idea of "missing"), a few negative premiums, a few scores above the 0-100 scale —
and run it two ways:

  * unguarded — compute the weighted average directly. It returns a confident, wrong number.
  * guarded   — validate the dataframe against a Pandera schema first (lazy, so it collects
                *all* violations), which raises a precise error naming every bad row before a
                single corrupt value reaches the calculation.

We measure the magnitude of the silent error, how many issues the schema catches, and what the
validation costs (its throughput in rows/second), so the "insurance premium" of defensive code
is itself a measured quantity.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pandera.pandas as pa  # noqa: E402

from perf import time_s  # noqa: E402

N_ROWS = 100_000
REGIONS = ["north", "south", "east", "west"]

# The schema is the codified version of every "I'll just eyeball it in a notebook" check.
SCHEMA = pa.DataFrameSchema({
    "policy_id": pa.Column(int, unique=True),
    "risk_score": pa.Column(float, pa.Check.in_range(0, 100)),
    "premium": pa.Column(float, pa.Check.gt(0)),
    "region": pa.Column(str, pa.Check.isin(REGIONS)),
})


def _clean_frame(seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "policy_id": np.arange(N_ROWS),
        "risk_score": rng.uniform(0, 100, N_ROWS),
        "premium": rng.uniform(100, 10_000, N_ROWS),
        "region": rng.choice(REGIONS, N_ROWS),
    })


def _dirty_frame(seed=0):
    """Inject impurities that do NOT raise: sentinels, negatives, out-of-range values."""
    df = _clean_frame(seed)
    rng = np.random.default_rng(seed + 1)
    # The dominant impurity is the classic one: "missing" risk encoded as -1 in the CSV,
    # which silently drags the portfolio's average risk down. Plus smaller doses of
    # sign-flipped premiums and off-scale scores, so the schema has several things to catch.
    miss = rng.choice(N_ROWS, N_ROWS * 6 // 100, replace=False)
    df.loc[miss, "risk_score"] = -1.0                     # "missing" encoded as -1
    neg = rng.choice(N_ROWS, N_ROWS // 100, replace=False)
    df.loc[neg, "premium"] = -df.loc[neg, "premium"]      # sign-flipped premiums
    over = rng.choice(N_ROWS, N_ROWS // 100, replace=False)
    df.loc[over, "risk_score"] = 250.0                    # off the 0-100 scale
    return df


def weighted_risk(df):
    """The pipeline's output: premium-weighted average risk score."""
    return float(np.average(df["risk_score"], weights=df["premium"]))


def run_unguarded(df):
    """No checks: whatever is in the frame flows straight into the answer."""
    return weighted_risk(df)


def run_guarded(df):
    """Validate first; on failure, raise a precise error instead of a wrong number."""
    SCHEMA.validate(df, lazy=True)        # raises SchemaErrors listing every violation
    return weighted_risk(df)


def measure(seed=0):
    clean = _clean_frame(seed)
    dirty = _dirty_frame(seed)
    truth = weighted_risk(clean)
    silent_wrong = run_unguarded(dirty)   # confident, corrupted

    # The guard turns the silent corruption into a loud, itemised failure.
    caught = 0
    try:
        run_guarded(dirty)
    except pa.errors.SchemaErrors as e:
        caught = len(e.failure_cases)

    # Cost of the insurance: validation throughput on the clean frame (the happy path).
    t_validate = time_s(lambda: SCHEMA.validate(clean, lazy=True), number=1, repeat=3)
    t_compute = time_s(lambda: weighted_risk(clean), number=1, repeat=5)
    return {
        "n_rows": N_ROWS,
        "truth": truth, "silent_wrong": silent_wrong,
        "rel_error_pct": abs(silent_wrong - truth) / truth * 100,
        "caught": caught,
        "validate_s": t_validate, "compute_s": t_compute,
        "validate_rows_per_s": N_ROWS / t_validate,
    }


def main():
    m = measure()
    print(f"premium-weighted average risk over {m['n_rows']:,} policies:\n")
    print(f"  truth (clean data)        : {m['truth']:.3f}")
    print(f"  unguarded on dirty data   : {m['silent_wrong']:.3f}  "
          f"({m['rel_error_pct']:.1f}% off — and no error raised)")
    print(f"  guarded on dirty data     : SchemaErrors — {m['caught']:,} violations caught\n")
    print(f"  validation cost: {m['validate_s']*1e3:.1f} ms for {m['n_rows']:,} rows "
          f"({m['validate_rows_per_s']/1e6:.2f}M rows/s)")
    print(f"  the bare computation took {m['compute_s']*1e3:.2f} ms")


if __name__ == "__main__":
    main()
