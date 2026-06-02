"""Chapter 4 - Exercise 4: probing sequence + collision trace (Example 4-4).

Task: reconstruct index_sequence, then for a first-letter hash and an 8-bucket
table:
  1. Insert Rome, San Francisco, New York, Barcelona -- show placements/probes.
  2. Lookup Johannesburg -- which indices get checked before "absent"?
  3. Delete Rome -- why a tombstone, not NULL?

Takeaway: probing makes a bucket's meaning depend on its neighbours. Deletion
must leave a tombstone so probe chains survive; NULL would terminate them early
and "lose" keys stored past the deleted slot.

Run: .venv/bin/python chapter_4/ex04_probing_trace.py
"""

TOMBSTONE = "<deleted>"


def index_sequence(hash_value, mask=0b111, perturb_shift=5):
    perturb = hash_value
    i = perturb & mask
    yield i
    while True:
        perturb >>= perturb_shift
        i = (i * 5 + perturb + 1) & mask
        yield i


def first_letter_hash(name):
    return ord(name[0])


class TinyDict:
    def __init__(self, size=8):
        self.size = size
        # each slot: None (empty) | TOMBSTONE | (key, value)
        self.slots: list[object] = [None] * size

    def insert(self, key, value, verbose=False):
        for i in index_sequence(first_letter_hash(key), self.size - 1):
            slot = self.slots[i]
            if slot is None or slot is TOMBSTONE or (isinstance(slot, tuple) and slot[0] == key):
                self.slots[i] = (key, value)
                if verbose:
                    print(f"  insert {key:<14} -> index {i}")
                return

    def lookup(self, key):
        checked: list[int] = []
        for i in index_sequence(first_letter_hash(key), self.size - 1):
            checked.append(i)
            slot = self.slots[i]
            if slot is None:
                return None, checked            # hit empty -> absent
            if isinstance(slot, tuple) and slot[0] == key:
                return slot[1], checked
        return None, checked

    def delete(self, key):
        for i in index_sequence(first_letter_hash(key), self.size - 1):
            slot = self.slots[i]
            if slot is None:
                return
            if isinstance(slot, tuple) and slot[0] == key:
                self.slots[i] = TOMBSTONE       # tombstone, NOT None
                return


def main():
    d = TinyDict(8)
    print("Inserting cities:")
    for city, country in [("Rome", "Italy"), ("San Francisco", "USA"),
                          ("New York", "USA"), ("Barcelona", "Spain")]:
        d.insert(city, country, verbose=True)
    print("slots:", d.slots)

    val, checked = d.lookup("Johannesburg")
    print(f"\nlookup Johannesburg -> {val}; indices checked: {checked}")

    print("\nDelete Rome (writes a tombstone)...")
    d.delete("Rome")
    print("slots:", d.slots)
    val, checked = d.lookup("Barcelona")
    print(f"lookup Barcelona after deleting Rome -> {val}; indices checked: {checked}")
    print("(Barcelona still found -- the probe skipped the tombstone instead of stopping.)")


if __name__ == "__main__":
    main()
