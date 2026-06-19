"""Chart for h01: IPython Parallel vs multiprocessing.Pool. Reuses benchmark.measure()."""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))   # repo root -> vizutil
sys.path.insert(0, str(HERE.parents[1]))   # chapter dir
sys.path.insert(0, str(HERE))

from vizutil import plt, setup, save, COLORS  # noqa: E402
import benchmark  # noqa: E402


def main():
    setup()
    out = benchmark.measure()
    confirmed, sr, cr, fr = benchmark.verdict(out)

    fig, (axs, axc) = plt.subplots(1, 2, figsize=(9.2, 4.0))
    pool_c, ipp_c = COLORS["teal"], COLORS["violet"]

    # left: startup (log scale — wildly different magnitudes)
    bars = axs.bar(["Pool", "IPython"], [out["pool_startup"], out["ipp_startup"]],
                   color=[pool_c, ipp_c])
    axs.set_yscale("log")
    axs.set_ylabel("startup seconds (log)")
    axs.set_title(f"startup cost\nPool {sr:.0f}x cheaper to spin up")
    for b, v in zip(bars, [out["pool_startup"], out["ipp_startup"]]):
        axs.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.2f}s",
                 ha="center", va="bottom", fontsize=9)

    # right: warm compute, grouped by granularity
    groups = ["coarse\n(8 tasks)", "fine\n(256 tasks)"]
    pool_v = [out["pool_coarse"], out["pool_fine"]]
    ipp_v = [out["ipp_coarse"], out["ipp_fine"]]
    x = range(len(groups))
    w = 0.38
    b1 = axc.bar([i - w / 2 for i in x], pool_v, w, color=pool_c, label="Pool")
    b2 = axc.bar([i + w / 2 for i in x], ipp_v, w, color=ipp_c, label="IPython")
    for bars in (b1, b2):
        for b in bars:
            axc.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{b.get_height():.2f}s",
                     ha="center", va="bottom", fontsize=8)
    axc.set_xticks(list(x)); axc.set_xticklabels(groups)
    axc.set_ylabel("warm compute seconds")
    axc.legend()
    axc.set_title(f"warm compute\ntie on coarse ({cr:.2f}x), Pool wins fine ({fr:.2f}x)")

    fig.suptitle("h01 — IPython Parallel vs multiprocessing.Pool on one machine",
                 fontsize=13, fontweight="bold")
    save(fig, __file__,
         subtitle=f"VERDICT: {'CONFIRMED' if confirmed else 'OVERTURNED'} — "
                  f"Pool starts {sr:.0f}x faster and is never slower on compute; "
                  "IPython Parallel's value is remote engines + interactivity, not local speed")


if __name__ == "__main__":
    main()
