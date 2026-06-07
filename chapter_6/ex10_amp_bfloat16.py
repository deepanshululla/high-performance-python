"""Chapter 6 - Exercise 10: bfloat16 trade-off + Automatic Mixed Precision (Examples 6-22, 6-26).

Task: (1) compare float16 vs bfloat16 with torch.finfo -- same 16 bits, different
split between range and precision; (2) use torch.amp.autocast to let torch pick a
lower precision per operation, and observe both the dtype "gotcha" and the speed.

Takeaway:
  * float16 and bfloat16 both cost 2 bytes, but bfloat16 trades precision for a
    huge range (max ~3.4e38, like float32) while float16 keeps precision but caps
    out at 65504. Deep learning usually wants range -> bfloat16.
  * autocast auto-casts eligible ops (matmul/conv) to low precision. The gotcha:
    inside autocast, mm(float32, float32) returns float16! Whether it is FASTER
    depends on hardware -- on CUDA the book sees ~3x; on this MPS GPU the matmul
    gain is marginal (Apple's float16 matmul throughput ~= float32). Measured, not
    assumed.

Run: .venv/bin/python chapter_6/ex10_amp_bfloat16.py
"""
import time

import torch

N = 4096


def pick_device():
    if torch.backends.mps.is_available():
        return "mps", torch.mps.synchronize
    if torch.cuda.is_available():
        return "cuda", torch.cuda.synchronize
    return "cpu", lambda: None


def timed(fn, sync, warmups=5, reps=20):
    for _ in range(warmups):
        fn()
        sync()
    best = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        sync()
        best = min(best, time.perf_counter() - t)
    return best


def main():
    device, sync = pick_device()
    print(f"Using device: {device}")

    # 1) float16 vs bfloat16: same size, different range/precision split.
    print("\nfloat16 vs bfloat16 (both 2 bytes):")
    for dt in (torch.float16, torch.bfloat16):
        fi = torch.finfo(dt)
        print(f"  {str(dt).replace('torch.', ''):9}: max {fi.max:11.4e}   "
              f"resolution {fi.resolution:<8}  (smaller step = more precision)")
    print("  -> bfloat16 sacrifices precision for float32-like range; float16 keeps")
    print("     precision but overflows at 65504. DL favors range -> bfloat16.")

    # 2) autocast: the dtype gotcha + measured speed.
    a = torch.rand(N, N, device=device)
    b = torch.rand(N, N, device=device)

    r32 = torch.mm(a, b)
    with torch.autocast(device_type=device):
        r_ac = torch.mm(a, b)
    print(f"\nautocast dtype gotcha: mm(float32, float32) normally -> {r32.dtype},")
    print(f"  but INSIDE autocast the same call -> {r_ac.dtype} (auto-downcast eligible op).")

    t32 = timed(lambda: torch.mm(a, b), sync)
    t_ac = timed(lambda: _amp_mm(a, b, device), sync)
    ah, bh = a.half(), b.half()
    t_half = timed(lambda: torch.mm(ah, bh), sync)
    print(f"\nmatmul {N}x{N} on {device}:")
    print(f"  float32:       {t32 * 1e3:7.3f} ms")
    print(f"  autocast:      {t_ac * 1e3:7.3f} ms   ({t32 / t_ac:.2f}x vs float32)")
    print(f"  manual .half(): {t_half * 1e3:6.3f} ms   ({t32 / t_half:.2f}x vs float32)")
    if t32 / t_half < 1.3:
        print("  -> little/no speedup here: this GPU's float16 matmul throughput is close to")
        print("     float32. On CUDA the book sees ~3x. autocast's VALUE is hardware-dependent;")
        print("     its mechanics (per-op precision selection) are the portable part.")
    else:
        print("  -> lower precision packs more data per transfer and uses faster kernels.")


def _amp_mm(a, b, device):
    with torch.autocast(device_type=device):
        return torch.mm(a, b)


if __name__ == "__main__":
    main()
