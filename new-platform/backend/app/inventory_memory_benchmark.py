"""Read-only, opt-in published inventory memory benchmark.

Run from new-platform/backend:
    python -m app.inventory_memory_benchmark

Fetches published GitHub source files only. No DB writes, orders or scans.
"""
import gc
import json
import os
import resource
import time
import tracemalloc

def main():
    if os.getenv("PDUFA_RUN_INVENTORY_MEMORY_BENCHMARK") != "1":
        raise SystemExit("Set PDUFA_RUN_INVENTORY_MEMORY_BENCHMARK=1 to run")
    from .source_workspace import workspace
    tracemalloc.start()
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    source = workspace()
    # Source-only benchmark: numbering requires the persistent identity database.
    # Never synthesize or reassign program IDs in CI.
    published = source
    after_prepare = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    count = len(published.get("pipeline", []))
    index = {row['id']: row for row in published.get('pipeline', [])}
    after_index = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    payload_size = len(json.dumps(published, separators=(",", ":"), default=str).encode())
    after_json = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_python, peak_traced = tracemalloc.get_traced_memory()
    print(json.dumps({
        "programs": count,
        "inventory_index_rows": len(index),
        "identity_numbering": "SKIPPED_REQUIRES_PERSISTENT_DATABASE",
        "payload_bytes": payload_size,
        "rss_peak_kib_before": before,
        "rss_peak_kib_after_prepare": after_prepare,
        "rss_peak_kib_after_index": after_index,
        "rss_peak_kib_after_json": after_json,
        "tracemalloc_peak_bytes": peak_traced,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "note": "Linux ru_maxrss is peak KiB; raw published source only; excludes persistent ID numbering, prepared snapshot and scoring"
    }, sort_keys=True))
    del source, published, index
    gc.collect()

if __name__ == "__main__":
    main()
