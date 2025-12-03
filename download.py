#!/usr/bin/env python3
import argparse
import sys

# try:
from clientdb import client
# except ImportError:
#     import client

client.set_server(server_url='http://54.169.91.191',api_token='EtadObqx4MRwCTLsTa_YWmTfUl24Jg57tngu_feXna4')


def download_best(args):
    calib_hash_id, run_id, created_at = client.get_best_run()

    print(f"[best] Best run: hashID={calib_hash_id}, runID={run_id}", file=sys.stderr)

    # Download the best calibration (new requirement)
    print(f"[best] Downloading calibration for {calib_hash_id}", file=sys.stderr)
    client.calibrations_download(
        hashID=calib_hash_id,
        output_folder=args.calib_folder,
    )

    # Download the best result
    print(f"[best] Downloading results for runID={run_id}", file=sys.stderr)
    client.results_download(
        hashID=calib_hash_id,
        runID=run_id,
        output_folder=args.data_folder,
    )

    # Return ONLY hashID and runID to stdout (for bash)
    print(f"{calib_hash_id} {run_id}")
    return 0


def download_latest(args):
    # 1. Get latest calibration metadata
    meta = client.calibrations_get_latest()
    if not meta:
        print("[latest] No calibrations found on the server.", file=sys.stderr)
        print("")  # keep stdout parse-safe
        return 1

    hash_id = meta["hashID"]

    print(f"[latest] Latest calibration is {hash_id}", file=sys.stderr)

    # 2. Download that calibration
    print(f"[latest] Downloading calibration for {hash_id}", file=sys.stderr)
    client.calibrations_download(
        hashID=hash_id,
        output_folder=args.calib_folder,
    )

    # 3. List all results for this calibration (already newest first)
    items = client.results_list(hashID=hash_id)
    if not items:
        print(f"[latest] No results found for {hash_id}", file=sys.stderr)
        print("")  # keep stdout clean
        return 1

    # Pick the first non-empty run_id
    run_id = None
    for row in items:
        if row.get("run_id"):
            run_id = row["run_id"]
            break

    if not run_id:
        print(f"[latest] No valid runID found for {hash_id}", file=sys.stderr)
        print("")  # keep stdout clean
        return 1

    print(f"[latest] Latest run is runID={run_id}", file=sys.stderr)

    # 4. Download the result ZIP
    print(f"[latest] Downloading results for {hash_id} {run_id}", file=sys.stderr)
    client.results_download(
        hashID=hash_id,
        runID=run_id,
        output_folder=args.data_folder,
    )

    # 5. Output ONLY hashID runID to stdout (for bash scripting)
    print(f"{hash_id} {run_id}")
    return 0



def download_specific(args):
    if not args.hashID or not args.runID:
        print("Error: specific mode requires HASHID and RUNID", file=sys.stderr)
        print("")  # keep stdout clean
        return 1

    hash_id = args.hashID
    run_id = args.runID

    print(f"[specific] Downloading calibration for {hash_id}", file=sys.stderr)
    client.calibrations_download(
        hashID=hash_id,
        output_folder=args.calib_folder,
    )

    print(f"[specific] Downloading results: hashID={hash_id}, runID={run_id}", file=sys.stderr)
    client.results_download(
        hashID=hash_id,
        runID=run_id,
        output_folder=args.data_folder,
    )

    # Return ONLY hashID and runID to stdout (for bash scripts)
    print(f"{hash_id} {run_id}")
    return 0



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["best", "latest", "specific"])
    parser.add_argument("hashID", nargs="?")
    parser.add_argument("runID", nargs="?")
    parser.add_argument("--data-folder", default="./data")
    parser.add_argument("--calib-folder", default="./data/calibrations")
    args = parser.parse_args()

    if args.mode == "best":
        return download_best(args)
    elif args.mode == "latest":
        return download_latest(args)
    else:
        return download_specific(args)


if __name__ == "__main__":
    raise SystemExit(main())
