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
    from .workspace_response import prepared
    from .assessment_service import get_index
    tracemalloc.start()
    started = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    source = workspace()
    published = prepared(source)
    after_prepare = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    count = len(published.get("pipeline", []))
    index = get_index()
    after_index = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    payload_size = len(json.dumps(published, separators=(",", ":"), default=str).encode())
    after_json = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_python, peak_traced = tracemalloc.get_traced_memory()
    print(json.dumps({
        "programs": count,
        "assessment_index_type": type(index).__name__,
        "payload_bytes": payload_size,
        "rss_peak_kib_before": before,
        "rss_peak_kib_after_prepare": after_prepare,
        "rss_peak_kib_after_index": after_index,
        "rss_peak_kib_after_json": after_json,
        "tracemalloc_peak_bytes": peak_traced,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "note": "Linux ru_maxrss is peak KiB; benchmark does not use PostgreSQL"
    }, sort_keys=True))
    del source, published, index
    gc.collect()

if __name__ == "__main__":
    main()
