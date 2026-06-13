"""Generate a chart for every Chapter 8 exercise and tile them into a dashboard.

Each exercise lives in its own folder (chapter_8_compiling_to_c/exNN_name/exNN_name.py).
This driver imports each module by path, REUSES its functions to measure the key
comparison, saves `chart.png` into that folder, then assembles `exercises_dashboard.png`
here. Compiled exercises (ex02 Cython, ex03 Cython+OpenMP, ex05 C) are built on demand by
the exercises themselves, so the first run pays those one-time compile costs.

Run: .venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py
     .venv/bin/python chapter_8_compiling_to_c/visualize_exercises.py --only ex03
"""
import argparse
import importlib.util
import pathlib
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0]))   # repo root -> vizutil, perf
sys.path.insert(0, str(HERE))               # chapter dir -> _julia

from vizutil import plt, setup, save, COLORS  # noqa: E402
import _julia  # noqa: E402

MAXITER = _julia.DEFAULT_MAXITER
GOOD, OK, SLOW, WARN = COLORS["teal"], COLORS["blue"], COLORS["gray"], COLORS["amber"]


def load(folder):
    """Import an exercise module by file path, adding its folder to sys.path first."""
    d = HERE / folder
    sys.path.insert(0, str(d))
    path = d / f"{folder}.py"
    spec = importlib.util.spec_from_file_location(folder, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def best(fn, number=1, repeat=3):
    b = float("inf")
    for _ in range(repeat):
        t = time.perf_counter()
        for _ in range(number):
            fn()
        b = min(b, (time.perf_counter() - t) / number)
    return b


def barlabels(ax, bars, vals, fmt="{:.0f}", dy=1.02):
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() * dy, fmt.format(v),
                ha="center", va="bottom", fontsize=8.5)


# ---------------------------------------------------------------- per exercise
def measure_ex01():
    m = load("ex01_julia_baseline")
    zs, cs = _julia.build_inputs()
    return {
        "abs(z) < 2": best(lambda: m.calc_abs(MAXITER, zs, cs), repeat=2),
        "re²+im² < 4": best(lambda: m.calc_expanded(MAXITER, zs, cs), repeat=2),
    }


def draw_ex01(ax, d):
    labels, vals = list(d), [v for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, WARN])
    ax.set_ylabel("seconds (lower better)")
    ax.set_title(f"ex01 — pure Python: 'strength reduction' is a {vals[1]/vals[0]:.1f}× LOSS")
    barlabels(ax, bars, vals, "{:.2f}s")


def measure_ex02():
    m = load("ex02_cython_pure_python")
    zs, cs = _julia.build_inputs()
    cy = m._cyjulia
    return {
        "v0 plain": best(lambda: cy.v0_plain(MAXITER, zs, cs), repeat=3),
        "v1 typed": best(lambda: cy.v1_typed(MAXITER, zs, cs), repeat=5),
        "v2 expand": best(lambda: cy.v2_expanded(MAXITER, zs, cs), repeat=5),
        "v3 nobnds": best(lambda: cy.v3_nobounds(MAXITER, zs, cs), repeat=5),
    }


def draw_ex02(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, OK, GOOD, GOOD])
    ax.set_yscale("log")
    ax.set_ylabel("ms (log)")
    ax.set_title(f"ex02 — Cython ladder: typing alone is {vals[0]/vals[1]:.0f}×")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex03():
    m = load("ex03_cython_numpy_openmp")
    m.ensure_built()
    import _cyjulia_np  # noqa: E402
    zs, cs = _julia.build_inputs_numpy()
    return {
        "serial": best(lambda: _cyjulia_np.serial(MAXITER, zs, cs), repeat=5),
        "OpenMP\nguided": best(lambda: _cyjulia_np.omp(MAXITER, zs, cs), repeat=5),
    }


def draw_ex03(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[OK, GOOD])
    ax.set_ylabel("ms (lower better)")
    ax.set_title(f"ex03 — Cython+numpy: OpenMP prange {vals[0]/vals[1]:.1f}×")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex04():
    m = load("ex04_numba_jit")
    zs, cs = _julia.build_inputs_numpy()
    out = np.empty(len(zs), dtype=np.int32)
    t0 = time.perf_counter()
    m.calc_numba(MAXITER, zs, cs, out)         # cold: compile + run
    cold = time.perf_counter() - t0
    warm = best(lambda: m.calc_numba(MAXITER, zs, cs, out), repeat=5)
    out_p = np.empty(len(zs), dtype=np.int32)
    m.calc_numba_par(MAXITER, zs, cs, out_p)   # parallel cold (discarded)
    par = best(lambda: m.calc_numba_par(MAXITER, zs, cs, out_p), repeat=5)
    return {"cold\n(compile)": cold, "warm": warm, "parallel": par}


def draw_ex04(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, OK, GOOD])
    ax.set_yscale("log")
    ax.set_ylabel("ms (log)")
    ax.set_title(f"ex04 — Numba: cold {vals[0]/vals[1]:.0f}× the warm cost")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex05():
    m = load("ex05_ffi_diffusion")
    m.ensure_built()
    D, dt, N = 1.0, 0.1, m.N
    out = {}
    for name, fn in [("numpy", m.evolve_numpy), ("ctypes", m.evolve_ctypes),
                     ("cffi", m.evolve_cffi)]:
        g, o = m.initial_grid(), np.zeros((N, N), dtype=np.double)
        out[name] = best(lambda fn=fn, g=g, o=o: fn(g, o, D, dt), number=200, repeat=5)
    return out


def draw_ex05(ax, d):
    labels, vals = list(d), [v * 1e6 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, OK, GOOD])
    ax.set_ylabel("µs / step (lower better)")
    ax.set_title(f"ex05 — FFI: C kernel {vals[0]/vals[2]:.1f}× over numpy")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex06():
    m = load("ex06_cython_annotate")
    r = m.collect()
    return {"plain": r["plain"]["inner"], "typed": r["typed"]["inner"]}


def draw_ex06(ax, d):
    labels, vals = list(d), list(d.values())
    bars = ax.bar(labels, vals, color=[SLOW, GOOD])
    ax.set_ylabel("inner-loop VM score")
    ax.set_title(f"ex06 — cython -a: inner loop {vals[0]}→{vals[1]}")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex07():
    m = load("ex07_prange_schedulers")
    m.ensure_built()
    import _cyjulia_sched  # noqa: E402
    zs, cs = _julia.build_inputs_numpy()
    return {"static": best(lambda: _cyjulia_sched.static(MAXITER, zs, cs), repeat=5),
            "dynamic": best(lambda: _cyjulia_sched.dynamic(MAXITER, zs, cs), repeat=5),
            "guided": best(lambda: _cyjulia_sched.guided(MAXITER, zs, cs), repeat=5)}


def draw_ex07(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, GOOD, GOOD])
    ax.set_ylabel("ms (lower better)")
    ax.set_title(f"ex07 — schedulers: static {vals[0] / min(vals):.1f}× the best")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex08():
    m = load("ex08_boundscheck")
    return {"checked": best(lambda: m.run(m._diffcy.checked), repeat=3) / m.STEPS,
            "unchecked": best(lambda: m.run(m._diffcy.unchecked), repeat=3) / m.STEPS}


def draw_ex08(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, GOOD])
    ax.set_ylabel("ms / step")
    ax.set_title(f"ex08 — boundscheck off: {vals[0] / vals[1]:.2f}×")
    barlabels(ax, bars, vals, "{:.2f}")


def measure_ex09():
    m = load("ex09_pythran")
    m.ensure_built()
    import julia_pythran  # noqa: E402
    zs, cs = _julia.build_inputs_numpy()
    out = np.empty(len(zs), dtype=np.int32)
    nb = m.make_numba()
    nb(MAXITER, zs, cs, out)   # warm the JIT
    return {"Pythran": best(lambda: julia_pythran.calc(MAXITER, zs, cs), repeat=5),
            "Numba\nwarm": best(lambda: nb(MAXITER, zs, cs, out), repeat=5)}


def draw_ex09(ax, d):
    labels, vals = list(d), [v * 1000 for v in d.values()]
    bars = ax.bar(labels, vals, color=[OK, GOOD])
    ax.set_ylabel("ms")
    ax.set_title("ex09 — Pythran vs Numba (same class)")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex10():
    m = load("ex10_cpython_extension")
    m.ensure_built()
    from cdiffusion import evolve as cpyext  # noqa: E402
    D, dt, N = 1.0, 0.1, m.N
    backs = [("numpy", m.evolve_numpy), ("ctypes", m.evolve_ctypes),
             ("CPython\next", lambda g, o, dt, D=1.0: cpyext(g, o, dt, D))]
    res = {}
    for name, fn in backs:
        g, o = m.initial_grid(), np.zeros((N, N), dtype=np.double)
        res[name] = best(lambda fn=fn, g=g, o=o: fn(g, o, dt, D), number=200, repeat=5)
    return res


def draw_ex10(ax, d):
    labels, vals = list(d), [v * 1e6 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, OK, GOOD])
    ax.set_ylabel("µs / step")
    ax.set_title(f"ex10 — CPython ext {vals[0] / vals[2]:.1f}× numpy")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex11():
    m = load("ex11_f2py_fortran")
    m.ensure_built()
    from diffusion_f import evolve as ev  # noqa: E402
    D, dt, N = 1.0, 0.1, m.N
    g_np, o_np = m.initial_grid("C"), np.zeros((N, N), dtype=np.double)
    g_f, o_f = m.initial_grid("F"), np.zeros((N, N), dtype=np.double, order="F")
    return {"numpy": best(lambda: m.evolve_numpy(g_np, o_np, D, dt), number=200, repeat=5),
            "Fortran\nf2py": best(lambda: ev(g_f, o_f, D, dt), number=200, repeat=5)}


def draw_ex11(ax, d):
    labels, vals = list(d), [v * 1e6 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, GOOD])
    ax.set_ylabel("µs / step")
    ax.set_title(f"ex11 — Fortran {vals[0] / vals[1]:.1f}× numpy")
    barlabels(ax, bars, vals, "{:.0f}")


def measure_ex12():
    m = load("ex12_rust_pyo3")
    m.ensure_built()
    import diffusion_rs  # noqa: E402
    D, dt = 1.0, 0.1
    g = m.initial_grid()
    return {"numpy": best(lambda: m.evolve_numpy(g, dt, D), number=200, repeat=5),
            "Rust\nPyO3": best(lambda: diffusion_rs.evolve(g, dt, D), number=200, repeat=5)}


def draw_ex12(ax, d):
    labels, vals = list(d), [v * 1e6 for v in d.values()]
    bars = ax.bar(labels, vals, color=[SLOW, GOOD])
    ax.set_ylabel("µs / step")
    ax.set_title(f"ex12 — Rust {vals[0] / vals[1]:.1f}× numpy")
    barlabels(ax, bars, vals, "{:.0f}")


EXERCISES = {
    "ex01": ("ex01_julia_baseline", measure_ex01, draw_ex01),
    "ex02": ("ex02_cython_pure_python", measure_ex02, draw_ex02),
    "ex03": ("ex03_cython_numpy_openmp", measure_ex03, draw_ex03),
    "ex04": ("ex04_numba_jit", measure_ex04, draw_ex04),
    "ex05": ("ex05_ffi_diffusion", measure_ex05, draw_ex05),
    "ex06": ("ex06_cython_annotate", measure_ex06, draw_ex06),
    "ex07": ("ex07_prange_schedulers", measure_ex07, draw_ex07),
    "ex08": ("ex08_boundscheck", measure_ex08, draw_ex08),
    "ex09": ("ex09_pythran", measure_ex09, draw_ex09),
    "ex10": ("ex10_cpython_extension", measure_ex10, draw_ex10),
    "ex11": ("ex11_f2py_fortran", measure_ex11, draw_ex11),
    "ex12": ("ex12_rust_pyo3", measure_ex12, draw_ex12),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="render a single exercise, e.g. ex03")
    args = ap.parse_args()
    setup()

    keys = [args.only] if args.only else list(EXERCISES)
    data = {}
    for k in keys:
        folder, measure, draw = EXERCISES[k]
        print(f"measuring {k} ...")
        d = measure()
        data[k] = d
        fig, ax = plt.subplots(figsize=(5, 3.6))
        draw(ax, d)
        save(fig, str(HERE / folder / "x.py"))   # writes chart.png into the folder

    if args.only:
        return

    # Dashboard: 3x4 grid (12 charts).
    fig, axes = plt.subplots(3, 4, figsize=(22, 13))
    flat = axes.flatten()
    for ax, k in zip(flat, EXERCISES):
        EXERCISES[k][2](ax, data[k])
    fig.suptitle("High Performance Python — Chapter 8: Compiling to C (12 exercises)",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = HERE / "exercises_dashboard.png"
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
