"""Chapter 7 - Exercise 1: scikit-learn vs raw lstsq for OLS (Examples 7-2..7-5).

Task: fit the same line (slope `m`) to a 14-element row two ways -- scikit-learn's
`LinearRegression` and a bare `numpy.linalg.lstsq` -- and time a single call to each.

Takeaway: both bottom out in the *identical* `linalg.lstsq` solve, yet sklearn is
many times slower. The gap is not the maths: it's the per-call safety net
(`_validate_data` + `_preprocess_data` -- NaN/Inf scanning, shape and sparsity
checks, mean-centering). When the actual computation is microscopic and you run it
hundreds of millions of times, it's validation, not arithmetic, that sets runtime.

Run: .venv/bin/python chapter_7/ex01_ols_sklearn_vs_lstsq/ex01_ols_sklearn_vs_lstsq.py
"""
import pathlib
import sys
import timeit
import warnings

import numpy as np
from sklearn.linear_model import LinearRegression

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from perf import human, peak_bytes  # noqa: E402

warnings.filterwarnings("ignore")


def gen_data(n_rows, n_days=14, seed=0):
    """Synthetic 'hours used per day': Poisson(60 minutes) / 60 -> continuous hours."""
    rng = np.random.default_rng(seed)
    return rng.poisson(60, size=(n_rows, n_days)) / 60.0


def ols_sklearn(row):
    """Solve OLS with scikit-learn's LinearRegression -- safe, general, checked."""
    est = LinearRegression()
    X = np.arange(row.shape[0]).reshape(-1, 1)   # shape (14, 1)
    est.fit(X, row)
    return est.coef_[0]


def ols_lstsq(row):
    """Solve OLS by calling numpy.linalg.lstsq directly -- no checks, just the solve."""
    X = np.arange(row.shape[0])
    ones = np.ones(row.shape[0])
    A = np.vstack((X, ones)).T                   # shape (14, 2)
    m, c = np.linalg.lstsq(A, row, rcond=-1)[0]
    return m


def main():
    row = gen_data(1)[0]                          # a single synthetic user's 14 days

    # Correctness: both methods recover the same slope to floating-point tolerance.
    m_sk, m_ls = ols_sklearn(row), ols_lstsq(row)
    assert np.isclose(m_sk, m_ls), (m_sk, m_ls)
    print(f"Both recover the same slope m = {m_ls:+.6f}  (sklearn agrees to {abs(m_sk - m_ls):.2e})")

    N = 2000
    t_sk = timeit.timeit(lambda: ols_sklearn(row), number=N) / N
    t_ls = timeit.timeit(lambda: ols_lstsq(row), number=N) / N

    print(f"\nPer-call cost (mean of {N:,} calls on one 14-element row):")
    print(f"  sklearn LinearRegression : {t_sk * 1e6:8.2f} us   peak {human(peak_bytes(lambda: ols_sklearn(row)))}")
    print(f"  numpy linalg.lstsq       : {t_ls * 1e6:8.2f} us   peak {human(peak_bytes(lambda: ols_lstsq(row)))}")
    print(f"  -> sklearn is {t_sk / t_ls:.1f}x slower, though both end in the same linalg.lstsq.")

    # The real dataset is 1,000,000 users x up to 730 windows == 730M OLS calls.
    calls = 1_000_000 * 730
    print(f"\nProjected to the book's full job ({calls:,} OLS calls):")
    print(f"  sklearn : {t_sk * calls / 3600:6.1f} hours")
    print(f"  lstsq   : {t_ls * calls / 3600:6.1f} hours")
    print("  -> the validation tax, not the solve, is the whole bill at scale.")


if __name__ == "__main__":
    main()
