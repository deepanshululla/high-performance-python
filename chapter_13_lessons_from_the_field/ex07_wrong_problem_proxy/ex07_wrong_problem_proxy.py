"""ex07 — the fastest optimisation is solving the right problem (Warmerdam's carts table).

Vincent Warmerdam's team spent weeks building a time-series ML system to predict how many
trucks would arrive at a warehouse — wrestling with holidays, seasonality, and a giant grid
search — and it only matched the existing manual method. In his last week he learned about a
"carts" table: suppliers *rent* carts three-to-five days before returning them full on a
truck. The number of carts rented was a near-perfect leading indicator. "We were solving the
wrong problem. This wasn't a machine learning problem; it was a SQL problem." Projecting the
rented-cart count a few days ahead, divided by carts-per-truck, beat the model at zero compute.

This drill reproduces that. Demand is generated with trend, yearly seasonality, weekday
effects, and holiday spikes; trucks arrive `LEAD` days after the carts for that demand are
rented, so `carts[d-LEAD] / CARTS_PER_TRUCK` predicts `trucks[d]` almost exactly. We then
compare:

  * ml_model — a gradient-boosting regressor with a grid search over calendar + autoregressive
               features (the data the team *had* before discovering carts). Minutes of the
               story compressed to seconds of compute, and it never sees the carts column.
  * proxy    — one line: shift the rented-cart count forward and divide. Microseconds.

Both are scored on the planning team's real cost function — the number of days the prediction
is off by more than `TOLERANCE` trucks — over the same held-out test period.
"""
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))   # repo root -> perf

import numpy as np  # noqa: E402
from sklearn.ensemble import HistGradientBoostingRegressor  # noqa: E402
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit  # noqa: E402

N_DAYS = 1500
LEAD = 3                # carts rented LEAD days before the truck arrives
CARTS_PER_TRUCK = 20
TOLERANCE = 15          # the discrete cost: a day "wrong" if off by more than this many trucks
TEST_DAYS = 300


def _make_data(seed=0):
    rng = np.random.default_rng(seed)
    d = np.arange(N_DAYS)
    dow = d % 7
    # Demand process: upward trend + yearly season + weekday pattern + holiday spikes + noise.
    trend = 1500 + 0.4 * d
    season = 300 * np.sin(2 * np.pi * d / 365.25)
    weekday = np.where(dow < 5, 200, -400)            # weekdays busy, weekends quiet
    holidays = np.zeros(N_DAYS)
    holiday_days = rng.choice(N_DAYS, size=N_DAYS // 40, replace=False)
    holidays[holiday_days] = rng.uniform(-900, 900, size=holiday_days.size)
    demand = trend + season + weekday + holidays + rng.normal(0, 60, N_DAYS)
    demand = np.clip(demand, 100, None)

    carts_rented = np.round(demand).astype(float)
    # Trucks arrive LEAD days after the carts for that demand were rented.
    trucks = np.empty(N_DAYS)
    trucks[:LEAD] = carts_rented[0] / CARTS_PER_TRUCK
    trucks[LEAD:] = carts_rented[:-LEAD] / CARTS_PER_TRUCK
    trucks = np.round(trucks + rng.normal(0, 1.0, N_DAYS))
    return d, dow, carts_rented, trucks, holidays


def _features(d, dow, trucks, holidays):
    """The features the team HAD: calendar for day d + autoregressive lags. No carts."""
    X = np.column_stack([
        d,                                  # trend
        np.sin(2 * np.pi * d / 365.25),     # yearly season
        np.cos(2 * np.pi * d / 365.25),
        dow,
        (dow < 5).astype(float),            # weekday flag
        (holidays != 0).astype(float),      # is today a holiday
        np.r_[trucks[0], trucks[:-1]],      # trucks lag-1
        np.r_[[trucks[0]] * 7, trucks[:-7]],  # trucks lag-7
    ])
    return X


def cost_days(pred, actual):
    """The planning team's cost: how many days the prediction is off by > TOLERANCE trucks."""
    return int(np.sum(np.abs(pred - actual) > TOLERANCE))


def run_model(d, dow, carts, trucks, holidays):
    """Grid-searched gradient boosting on calendar + autoregressive features."""
    X = _features(d, dow, trucks, holidays)
    Xtr, Xte = X[:-TEST_DAYS], X[-TEST_DAYS:]
    ytr, yte = trucks[:-TEST_DAYS], trucks[-TEST_DAYS:]
    grid = {
        "max_depth": [2, 3, 4],
        "learning_rate": [0.05, 0.1],
        "max_iter": [100, 300],
    }
    search = GridSearchCV(
        HistGradientBoostingRegressor(random_state=0),
        grid, cv=TimeSeriesSplit(n_splits=4), scoring="neg_mean_absolute_error",
    )
    t0 = time.perf_counter()
    search.fit(Xtr, ytr)
    pred = search.predict(Xte)
    secs = time.perf_counter() - t0
    return cost_days(pred, yte), secs, len(search.cv_results_["params"])


def run_proxy(d, dow, carts, trucks, holidays):
    """The SQL one-liner: trucks[d] ~ carts rented LEAD days ago / carts per truck."""
    t0 = time.perf_counter()
    pred_all = np.r_[[carts[0]] * LEAD, carts[:-LEAD]] / CARTS_PER_TRUCK
    pred = pred_all[-TEST_DAYS:]
    secs = time.perf_counter() - t0
    return cost_days(pred, trucks[-TEST_DAYS:]), secs


def measure(seed=0):
    data = _make_data(seed)
    model_cost, model_s, n_fits = run_model(*data)
    proxy_cost, proxy_s = run_proxy(*data)
    return {
        "test_days": TEST_DAYS, "tolerance": TOLERANCE, "n_grid": n_fits,
        "model": {"bad_days": model_cost, "seconds": model_s},
        "proxy": {"bad_days": proxy_cost, "seconds": proxy_s},
        "speedup": model_s / proxy_s,
    }


def main():
    m = measure()
    print(f"predicting truck arrivals over {m['test_days']} held-out days "
          f"(a day is 'wrong' if off by > {m['tolerance']} trucks):\n")
    md, px = m["model"], m["proxy"]
    print(f"  ML grid search ({m['n_grid']} param sets): "
          f"{md['bad_days']:3d} bad days   {md['seconds']:7.2f} s")
    print(f"  carts proxy (one line)            : "
          f"{px['bad_days']:3d} bad days   {px['seconds']:.6f} s")
    print(f"\n  the proxy is {m['speedup']:,.0f}x less compute and "
          f"{'better' if px['bad_days'] <= md['bad_days'] else 'worse'} on the real metric")


if __name__ == "__main__":
    main()
