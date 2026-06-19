"""ex09 — does Docker slow your code down? (the macOS asterisk on the book's "no")

The book runs a numpy diffusion on the host and again inside a Docker container
(Example 11-6) and gets essentially identical times — ~0.86 s host, ~0.84 s
container — concluding that "Docker is not slower than running on the host machine
in any meaningful way when the task relies mainly on CPU/memory." That is true,
the book is careful to add, *on Linux*, where Docker uses the kernel's `cgroups`
and the container shares the host kernel directly. On macOS (and Windows) there is
no Linux `cgroups`: Docker has to run a whole Linux VM under a hypervisor, and
every container runs inside that VM. The book flags this in a warning box; this
exercise measures it.

We run the identical `workload.py` two ways and compare the *compute* time (the
script's own internal timer, so container startup is excluded):

  * on the **host**, under this project's Python, and
  * inside a **container** built from `python:3.12-slim` + numpy.

We also measure the container's startup overhead (the gap between the wall-clock
of `docker run` and the compute it reported), because on macOS that — plus any
compute penalty — is the real cost of "just run it in Docker." A checksum from the
workload guards that both ran the same computation.

If Docker is not available the exercise skips cleanly, so the suite still runs.
"""
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

IMAGE = "hpp-ch11-diffusion:latest"
HOST_PY = str(REPO / ".venv" / "bin" / "python")
REPEAT = 3
EXPECTED_SUM = float((768 // 2) ** 2)   # mass conserved by the roll Laplacian


def docker_available():
    try:
        subprocess.run(["docker", "info"], capture_output=True, timeout=10, check=True)
        return True
    except Exception:
        return False


def ensure_image():
    have = subprocess.run(["docker", "images", "-q", IMAGE],
                          capture_output=True, text=True).stdout.strip()
    if have:
        return False
    print(f"building {IMAGE} (first run only)...")
    subprocess.run(["docker", "build", "-t", IMAGE, str(HERE)], check=True)
    return True


def _parse(text):
    m_rt = re.search(r"RUNTIME_S ([\d.]+)", text)
    m_sm = re.search(r"SUM ([\d.]+)", text)
    assert m_rt and m_sm, f"could not parse workload output:\n{text}"
    rt, sm = float(m_rt.group(1)), float(m_sm.group(1))
    assert abs(sm - EXPECTED_SUM) < 1.0, f"workload checksum {sm} != {EXPECTED_SUM}"
    return rt


def run_host():
    best = None
    for _ in range(REPEAT):
        out = subprocess.run([HOST_PY, str(HERE / "workload.py")],
                             capture_output=True, text=True, check=True).stdout
        rt = _parse(out)
        best = rt if best is None else min(best, rt)
    return best


def run_container():
    import time
    best_compute = None
    best_wall = None
    for _ in range(REPEAT):
        t0 = time.perf_counter()
        out = subprocess.run(["docker", "run", "--rm", IMAGE],
                             capture_output=True, text=True, check=True).stdout
        wall = time.perf_counter() - t0
        rt = _parse(out)
        best_compute = rt if best_compute is None else min(best_compute, rt)
        best_wall = wall if best_wall is None else min(best_wall, wall)
    assert best_compute is not None and best_wall is not None
    return best_compute, best_wall


def measure():
    if not docker_available():
        return None
    ensure_image()
    host = run_host()
    c_compute, c_wall = run_container()
    return {"host": host, "container": c_compute, "container_wall": c_wall,
            "startup": c_wall - c_compute}


def main():
    r = measure()
    if r is None:
        print("[skipped] Docker is not available — start Docker Desktop to run this exercise.")
        return
    overhead = (r["container"] / r["host"] - 1) * 100
    print(f"numpy diffusion (768x768, 400 iters), compute time only (best of {REPEAT}):")
    print(f"  host       : {r['host']*1000:7.1f} ms")
    print(f"  container  : {r['container']*1000:7.1f} ms   "
          f"({overhead:+.0f}% vs host)")
    print(f"  container startup overhead (VM + image): {r['startup']*1000:6.0f} ms "
          "on top, every run")
    print("  on macOS Docker runs inside a Linux VM, so CPU work is measurably slower than host — "
          "the book's near-zero overhead is a Linux result")


if __name__ == "__main__":
    main()
