"""Probabilistic data structures, ported from the book's Chapter 12 listings.

These are the simple, unoptimised reference implementations the book presents — a
Morris counter, a Bloom filter (plus a scaling variant), and the LogLog family
(LogLogRegister, LL, HyperLogLog), with a small K-Minimum-Values cardinality
estimator added for comparison. They trade accuracy for memory: each stores a
compact sketch instead of the data, answering one narrow question (an approximate
count, a "have I seen this?", a cardinality) in kilobytes where an exact structure
would need gigabytes.

The exercises (ex08-ex10) import these and measure their error empirically. We use
`mmh3` (MurmurHash3) for hashing throughout, as the book does. The K-Minimum-Values
class uses a stdlib `bisect`-maintained sorted list instead of the book's `blist`
dependency, which is no longer maintained.
"""
import bisect
import math
import random

import mmh3

UINT32_MAX = 2 ** 32 - 1


# --------------------------------------------------------------------------- Morris

class MorrisCounter:
    """Approximate counter storing an exponent; the value it represents is 2**exponent.

    Each increment ticks the exponent up only with probability 1/2**exponent, so the
    exponent tracks log2(count) and a single byte counts to ~2**255.
    """

    def __init__(self, nbr_counters=1):
        # 'B' = unsigned char, 1 byte per counter — the whole point of the structure.
        import array
        self.exponents = array.array("B", [0] * nbr_counters)

    def __len__(self):
        return len(self.exponents)

    def get(self, counter=0):
        return 2 ** self.exponents[counter]

    def add(self, counter=0):
        value = self.get(counter)
        if random.uniform(0, 1) < 1.0 / value:
            self.exponents[counter] += 1


# --------------------------------------------------------------------------- Bloom

class BloomFilter:
    """Probabilistic set membership: no false negatives, a tunable false-positive rate."""

    def __init__(self, capacity, error=0.005):
        import bitarray
        self.capacity = capacity
        self.error = error
        self.num_bits = int((-capacity * math.log(error)) // math.log(2) ** 2 + 1)
        self.num_hashes = int((self.num_bits * math.log(2)) // capacity + 1)
        self.data = bitarray.bitarray(self.num_bits)
        self.data.setall(False)

    def _indexes(self, key):
        h1, h2 = mmh3.hash64(_as_bytes(key))
        for i in range(self.num_hashes):
            yield (h1 + i * h2) % self.num_bits

    def add(self, key):
        for index in self._indexes(key):
            self.data[index] = True

    def __contains__(self, key):
        return all(self.data[index] for index in self._indexes(key))

    def __len__(self):
        bit_on = self.data.count(True)
        bit_off_percent = 1.0 - bit_on / self.num_bits
        if bit_off_percent == 0:
            return self.capacity
        return int(-1.0 * self.num_bits * math.log(bit_off_percent) / self.num_hashes)

    def num_bytes(self):
        return self.num_bits // 8 + 1


class ScalingBloomFilter:
    """Chains Bloom filters with tightening error rates so capacity can grow on demand."""

    def __init__(self, capacity, error=0.005, max_fill=0.8, error_tightening_ratio=0.5):
        self.capacity = capacity
        self.base_error = error
        self.max_fill = max_fill
        self.error_tightening_ratio = error_tightening_ratio
        self.bloom_filters = []
        self.current_bloom = None
        self._add_bloom()

    def _add_bloom(self):
        new_error = self.base_error * self.error_tightening_ratio ** len(self.bloom_filters)
        bloom = BloomFilter(self.capacity, new_error)
        self.bloom_filters.append(bloom)
        self.current_bloom = bloom
        return bloom

    def add(self, key):
        if key in self:
            return True
        self.current_bloom.add(key)
        if len(self.current_bloom) >= int(self.current_bloom.capacity * self.max_fill):
            self._add_bloom()
        return False

    def __contains__(self, key):
        return any(key in bloom for bloom in self.bloom_filters)

    def num_bytes(self):
        return sum(b.num_bytes() for b in self.bloom_filters)


# --------------------------------------------------------------------------- LogLog

def trailing_zeros(number):
    """Index of the lowest set bit of a 32-bit int (32 if the number is zero)."""
    if not number:
        return 32
    index = 0
    while (number >> index) & 1 == 0:
        index += 1
    return index


class LogLogRegister:
    """A single LogLog 'coin flipper': remembers the longest run of trailing zeros seen."""

    counter = 0

    def add(self, item):
        self._add(mmh3.hash(_as_str(item), signed=False))

    def _add(self, item_hash):
        # rho = position of the first set bit, 1-indexed (trailing_zeros + 1). The
        # book's printed listing stores the 0-indexed trailing_zeros, which biases the
        # harmonic estimate low by ~2x; the +1 is what its accurate Table 12-3 run used.
        bit_index = trailing_zeros(item_hash) + 1
        if bit_index > self.counter:
            self.counter = bit_index

    def __len__(self):
        return 2 ** self.counter


class LL:
    """Classic LogLog: 2**p registers, each a flipper, combined by an averaging estimate."""

    # Bias constants: HyperLogLog's harmonic estimate uses ALPHA (the book's 0.7213
    # form); classic LogLog's arithmetic-mean estimate needs its own ~0.39701 (the book
    # reuses 0.7213 for both, which overestimates LogLog by ~1.8x — fixed here).
    ALPHA_LOGLOG = 0.39701

    def __init__(self, p):
        self.p = p
        self.num_registers = 2 ** p
        self.registers = [LogLogRegister() for _ in range(self.num_registers)]
        self.alpha = 0.7213 / (1.0 + 1.079 / self.num_registers)

    def add(self, item):
        item_hash = mmh3.hash(_as_str(item), signed=False)
        register_index = item_hash & (self.num_registers - 1)
        register_hash = item_hash >> self.p
        self.registers[register_index]._add(register_hash)

    def __len__(self):
        register_sum = sum(h.counter for h in self.registers)
        return int(self.num_registers * self.ALPHA_LOGLOG
                   * 2 ** (register_sum / self.num_registers))

    def num_bytes(self):
        # one register stores a small count; the book bounds it at ~5 bits, so ~1 byte.
        return self.num_registers


class HyperLogLog(LL):
    """HyperLogLog: harmonic (spherical) averaging plus small/large-range corrections."""

    def __len__(self):
        indicator = sum(2 ** -m.counter for m in self.registers)
        E = self.alpha * (self.num_registers ** 2) / indicator
        if E <= 5.0 / 2.0 * self.num_registers:
            V = sum(1 for m in self.registers if m.counter == 0)
            Estar = (self.num_registers * math.log(self.num_registers / float(V), 2)
                     if V != 0 else E)
        else:
            if E <= 2 ** 32 / 30.0:
                Estar = E
            else:
                Estar = -2 ** 32 * math.log(1 - E / 2 ** 32, 2)
        return int(Estar)


# --------------------------------------------------------------------------- KMV

class KMinValues:
    """Cardinality via the k smallest unique hashes: even spacing implies the count."""

    def __init__(self, num_hashes):
        self.num_hashes = num_hashes
        self.data = []                       # sorted, unique, length <= num_hashes

    def add(self, item):
        h = mmh3.hash(_as_str(item), signed=False)
        i = bisect.bisect_left(self.data, h)
        if i < len(self.data) and self.data[i] == h:
            return                            # already seen -> idempotent
        bisect.insort(self.data, h)
        if len(self.data) > self.num_hashes:
            self.data.pop()                   # drop the largest

    def __len__(self):
        if len(self.data) <= 2:
            return 0
        return int((self.num_hashes - 1) * UINT32_MAX / self.data[-1])

    def num_bytes(self):
        return self.num_hashes * 4            # 32-bit hashes


# --------------------------------------------------------------------------- helpers

def _as_bytes(key):
    return key if isinstance(key, bytes) else str(key).encode()


def _as_str(item):
    return item if isinstance(item, str) else str(item)


if __name__ == "__main__":
    # quick smoke test: each structure should land in the right ballpark for 100k items.
    random.seed(0)
    mc = MorrisCounter()
    for _ in range(1000):
        mc.add()
    print("Morris after 1000 adds ~", mc.get())

    bf = BloomFilter(1000, error=0.01)
    for i in range(1000):
        bf.add(f"item-{i}")
    print("Bloom contains item-500:", "item-500" in bf,
          "  num_bytes:", bf.num_bytes())

    hll = HyperLogLog(10)
    for i in range(100_000):
        hll.add(i)
    print("HyperLogLog estimate of 100000 unique:", len(hll))

    kmv = KMinValues(1024)
    for i in range(100_000):
        kmv.add(i)
    print("KMinValues estimate of 100000 unique:", len(kmv))
