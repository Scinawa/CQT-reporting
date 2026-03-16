#!/usr/bin/env python3
"""
Metadata-only poll: checks the DB for the latest run_id WITHOUT downloading anything.
Outputs "<hash_id> <run_id>" to stdout on success, empty string on no data.

Used by run_benchmarking.sh as the PRIMARY bandwidth guard — download.py is only
called after this confirms a new run_id exists.
"""
import os
import sys
from clientdb import client

client.set_server(
    server_url=os.environ["CQT_SERVER_URL"],
    api_token=os.environ["CQT_API_TOKEN"],
)


def main():
    # Step 1: get latest calibration metadata (no download)
    meta = client.calibrations_get_latest()
    if not meta:
        print("", flush=True)
        print("[poll] No calibrations found on server.", file=sys.stderr)
        return 1

    hash_id = meta["hashID"]

    # Step 2: list results for this calibration (no download)
    items = client.results_list(hashID=hash_id)
    if not items:
        print("", flush=True)
        print(f"[poll] No results found for {hash_id}.", file=sys.stderr)
        return 1

    # Pick the first non-empty run_id (list is newest first)
    run_id = None
    for row in items:
        if row.get("run_id"):
            run_id = row["run_id"]
            break

    if not run_id:
        print("", flush=True)
        print(f"[poll] No valid run_id found for {hash_id}.", file=sys.stderr)
        return 1

    # Output to stdout for bash to consume
    print(f"{hash_id} {run_id}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
