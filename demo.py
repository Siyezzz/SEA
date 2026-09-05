"""Synthetic lifecycle demonstration, not a learning benchmark."""
from kernel import Kernel

k = Kernel()
mid = k.add("demo", "CSV encoding", "Inspect the encoding before parsing CSV.",
            "synthetic:fixture", "discovery")
print("Before validation:", repr(k.recall("CSV", "demo")))
for i in range(3):
    k.feedback(mid, f"synthetic-heldout-{i}", 1, "synthetic:passed")
print("After validation:", k.recall("CSV", "demo"))
k.archive("demo")
print("After archive:", repr(k.recall("CSV", "demo")))
print("Explicit archive lookup:", k.recall("CSV", "demo", include_archived=True))
k.close()
