import os
import io
import json
import base64
import zipfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import requests
import time 
from tabulate import tabulate
import re


CFG_PATHS = [
    Path(os.getenv("QIBO_CLIENT_CONFIG", "")) if os.getenv("QIBO_CLIENT_CONFIG") else None,
    Path.home() / ".qibo_client.json",
    Path.cwd() / ".qibo_client.json",
]
CFG_PATHS = [p for p in CFG_PATHS if p is not None]


def _read_cfg() -> dict:
    """Return the merged client configuration from the first readable config path.

    Search order:
      1) env var QIBO_CLIENT_CONFIG (if set)
      2) ~/.qibo_client.json
      3) ./ .qibo_client.json

    Returns:
        dict: Parsed JSON configuration or {} if not found.
    """
    for p in CFG_PATHS:
        try:
            if p.exists():
                with open(p, "r") as f:
                    return json.load(f)
        except Exception:
            continue
    return {}


def _write_cfg(data: dict) -> None:
    """Write client configuration to a persistent file.

    Target path:
      - If QIBO_CLIENT_CONFIG is set, write there.
      - Otherwise, write to ~/.qibo_client.json

    Args:
        data: Configuration dictionary to write.
    """
    target = None
    if os.getenv("QIBO_CLIENT_CONFIG"):
        target = Path(os.getenv("QIBO_CLIENT_CONFIG"))
    else:
        target = Path.home() / ".qibo_client.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w") as f:
        json.dump(data, f, indent=2)


def set_server(server_url: str, api_token: Optional[str] = None) -> None:
    """Persist the default server URL and optional API token for this client.

    The values are saved to a JSON config file so that subsequent function calls
    can omit the `server_url` and `api_token` parameters.

    Args:
        server_url: Base URL of the server (e.g., "http://127.0.0.1:5050").
        api_token: Optional bearer token for Authorization header.
    """
    data = _read_cfg()
    data["server_url"] = server_url.rstrip("/")
    if api_token is not None:
        data["api_token"] = api_token
    _write_cfg(data)


def _get_defaults(server_url: Optional[str], api_token: Optional[str]) -> Tuple[str, Optional[str]]:
    """Resolve server_url and api_token from arguments or persisted config.

    Args:
        server_url: Optional explicit server URL.
        api_token: Optional explicit token.

    Returns:
        (server_url, api_token): Final values after consulting config.
    """
    cfg = _read_cfg()
    return (
        server_url.rstrip("/") if server_url else cfg.get("server_url", "http://127.0.0.1:5050"),
        api_token if api_token is not None else cfg.get("api_token")
    )


def _auth_headers(api_token: Optional[str]) -> dict:
    """Build Authorization header dict if a token is provided."""
    return {"Authorization": f"Bearer {api_token}"} if api_token else {}


def calibrations_upload(
    hashID: str,
    calibrations_folder: str,
    notes: Optional[str] = "calibration params",
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> dict:
    """
    Create a ZIP from <calibrations_folder>/<hashID> (recursively) and upload
    it as a calibration bundle.

    Args:
        hashID: Unique identifier for the calibration record.
        notes: Free-form notes associated with this upload.
        calibrations_folder: Root folder containing hashID subfolders.
                            Expected structure:
                                calibrations_folder/
                                    <hashID>/
                                        ... files/subfolders ...
        server_url: Base server URL.
        api_token: Optional bearer token.

    Raises:
        FileNotFoundError: If <calibrations_folder>/<hashID> does not exist.
        NotADirectoryError: If it is not a directory.
        requests.HTTPError: If the server returns an error.

    Returns:
        dict: Server JSON response.
    """

    server_url, api_token = _get_defaults(server_url, api_token)

    # Expected folder structure: <calibrations_folder>/<hashID>
    root = Path(calibrations_folder)
    target_folder = root / hashID

    if not target_folder.exists():
        raise FileNotFoundError(f"Calibration subfolder not found: {target_folder}")
    if not target_folder.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target_folder}")

    # Create in-memory ZIP of the hashID folder
    mem_zip = io.BytesIO()
    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(target_folder):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(target_folder)
                zf.write(file_path, arcname=str(arcname))

    mem_zip.seek(0)
    zip_data = mem_zip.read()

    files_payload = {
        "archive": ("calibration_bundle.zip", zip_data, "application/zip")
    }
    data_payload = {"hashID": hashID, "notes": notes or ""}
    url = server_url + "/calibrations/upload"

    resp = requests.post(
        url,
        data=data_payload,
        files=files_payload,
        headers=_auth_headers(api_token),
        timeout=300,
    )

    if resp.status_code >= 400:
        raise requests.HTTPError(f"Upload failed ({resp.status_code}): {resp.text}")

    return resp.json()


def upload_all_calibrations(calibrations_folder: str) -> None:
    """
    Upload all calibration directories contained in the given folder.

    This function scans the specified `calibrations_folder` for subdirectories
    whose names are exactly 40 characters long (treated as a unique hash ID).
    For each such subfolder, it calls `calibrations_upload()` with:
      - hashID  = subfolder name
      - notes   = "calibration params"
      - calibrations_folder = full path to the calibrations directory

    A short 100 ms delay is inserted after each upload to avoid overloading
    the API or server.

    Parameters
    ----------
    calibrations_folder : str
        Path to the root folder containing calibration subdirectories.

    Returns
    -------
    None
    """
    calibrations_dir = Path(calibrations_folder)
    resp_list = []
    for subfolder in calibrations_dir.iterdir():
        if subfolder.is_dir() and len(subfolder.name) == 40:
            # print(subfolder.name)
            # print(str(subfolder))

            resp = calibrations_upload(
                hashID=subfolder.name,
                calibrations_folder=calibrations_folder
            )
            # print(resp)
            resp_list.append(resp)
            # time.sleep(0.1)  # 100 ms delay
    # print_table(resp_list)


def calibrations_list(server_url: Optional[str] = None, api_token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return metadata for last 20 calibration uploads (newest first).

    Args:
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error.

    Returns:
        List of dicts with keys:
          - id (int)
          - hashID (str)
          - notes (str | None)
          - created_at (str)
          - filename (str)
          - size (int)  # size of stored ZIP in bytes
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/list"
    r = requests.get(url, headers=_auth_headers(api_token), timeout=120)
    if r.status_code >= 400:
        raise requests.HTTPError(f"List failed ({r.status_code}): {r.text}")
    return r.json().get("items", [])


def calibrations_download(
    hashID: str,
    output_folder: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Tuple[Optional[str], str, str, bytes]:
    """
    Download the latest calibration ZIP for a given `hashID`, save it into a
    folder named <output_folder>/<hashID>, and unzip it there.

    Behavior:
      - If <output_folder>/<hashID> already exists:
            prints "calibration exists, skipping download"
            returns safely without downloading.
      - Otherwise:
            downloads the ZIP, creates the folder, unzips it.

    Returns:
        (notes, filename, created_at, data_bytes)
    """

    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/download"

    # Check if folder already exists → skip download
    target_dir = Path(output_folder) / hashID
    if target_dir.exists():
        # print("calibration exists, skipping download")
        return (None, "", "", b"")

    # Request download from the server
    r = requests.post(
        url,
        json={"hashID": hashID},
        headers=_auth_headers(api_token),
        timeout=300,
    )
    if r.status_code >= 400:
        raise requests.HTTPError(
            f"Download failed ({r.status_code}): {r.text}"
        )

    payload = r.json()

    notes = payload.get("notes")
    filename = payload["filename"]
    created_at = payload["created_at"]
    data_bytes = base64.b64decode(payload["data_b64"])

    # Create <output_folder>/<hashID> and unzip
    unzip_bytes_to_folder(data_bytes, str(target_dir))
    # print ("calibration downloaded")
    return (notes, filename, created_at, data_bytes)



def calibrations_get_latest(
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> Dict[str, Any]:
    """Return metadata for the most recently uploaded calibration.

    Args:
        server_url: Optional override for the server base URL.
        api_token: Optional override for the bearer token.

    Raises:
        requests.HTTPError: On server error (>=400).

    Returns:
        Dict with keys:
          - hashID (str)
          - notes (str | None)
          - created_at (str)
        If no calibrations exist, returns {}.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/calibrations/latest"
    r = requests.get(url, headers=_auth_headers(api_token), timeout=120)
    if r.status_code == 404:
        return {}
    if r.status_code >= 400:
        raise requests.HTTPError(f"Latest failed ({r.status_code}): {r.text}")
    return r.json()


def results_upload(
    hashID: str,
    runID: str,
    data_folder: str,
    name: Optional[str] = "experiment_group",
    notes: Optional[str] = "benchmarking",
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> dict:
    """
    Create a ZIP from the folder <data_folder>/<hashID>/<runID> and upload it
    as a 'result' bundle.

    Folder layout:
        data_folder/
            <hashID>/
                <runID>/
                    ... files and subfolders ...

    Args:
        hashID: Required. Identifier tying related results together.
        name: Required. Logical name/group for this particular result. 
                Use "experiment_group" if you are uploading a group of experiment results under a single runID
        notes: Free-form notes.
        data_folder: Root data folder which contains hashID/runID subfolders.
        runID: Required. The run identifier; must correspond to a subfolder
               under <data_folder>/<hashID>.
        server_url: Override server URL; otherwise use stored default.
        api_token: Override API token; otherwise use stored default.

    Returns:
        dict with keys like:
          {
            "status": "ok",
            "id": <int>,
            "created_at": "<timestamp>",
            "run_id": "<runID or null>"
          }
    """
    server_url, api_token = _get_defaults(server_url, api_token)

    if not runID:
        raise ValueError("runID must be provided and non-empty.")

    # Target folder: <data_folder>/<hashID>/<runID>
    root = Path(data_folder)
    run_dir = root / hashID / runID

    if not run_dir.exists():
        raise FileNotFoundError(f"Run folder not found: {run_dir}")
    if not run_dir.is_dir():
        raise NotADirectoryError(f"Run path is not a directory: {run_dir}")

    # Create in-memory ZIP from run_dir (recursive)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, dirs, files in os.walk(run_dir):
            r_path = Path(r)
            for file in files:
                full_path = r_path / file
                # Store paths relative to run_dir inside the ZIP
                arcname = full_path.relative_to(run_dir)
                zf.write(full_path, arcname=str(arcname))

    mem.seek(0)
    zip_bytes = mem.read()

    url = server_url + "/results/upload"
    multipart = {
        "hashID": (None, hashID),
        "name": (None, name),
        "notes": (None, notes or ""),
        "archive": ("bundle.zip", zip_bytes, "application/zip"),
        "runID": (None, runID),
    }

    r = requests.post(
        url,
        files=multipart,
        headers=_auth_headers(api_token),
        timeout=300,
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Upload failed ({r.status_code}): {r.text}")
    return r.json()



def upload_all_experiment_runs(data_folder: str) -> None:
    """
    Upload experiment-run data for all experiment groups within the given directory,
    processing experiment-run folders in increasing numeric order.

    This function expects the following directory structure:

        data_folder/
            <hashID_40_chars>/
                <runID_14_chars>/     (runID may include non-numeric characters)
                    ... data files ...

    Behavior
    --------
    * The function scans `data_folder` for subfolders whose names are exactly
      40 characters long — these are treated as experiment group IDs (hashID).
    * Inside each experiment group folder, it identifies valid experiment-run
      folders whose names are exactly 14 characters long.
    * For each run folder, the function attempts to extract a numeric value:
          - If runID is fully numeric → use int(runID)
          - Else → extract the first integer substring using regex
          - If no digits exist → the run is skipped
    * Experiment runs are sorted by the extracted integer key.
    * For each sorted run folder, the function calls:
          results_upload(hashID=<group>, runID=<run>, data_folder=<root>)
    * Responses are collected and shown in a summary table.

    Parameters
    ----------
    data_folder : str
        Path to the root directory containing experiment groups and run subfolders.

    Notes
    -----
    * This allows run IDs like:
          "00000000000042"
          "run_0015_data"
          "abc123xyz789"
      and sorts them by the extracted integer.
    """

    def extract_int_from_string(s: str) -> int | None:
        """Return the first integer found in a string, or None if no digits exist."""
        match = re.search(r"\d+", s)
        return int(match.group()) if match else None

    data_dir = Path(data_folder)
    resp_list = []

    for subfolder in data_dir.iterdir():
        if subfolder.is_dir() and len(subfolder.name) == 40:

            # Collect valid experiment-run directories + extracted integer
            experun_dirs = []
            for exprun in subfolder.iterdir():
                if exprun.is_dir() and len(exprun.name) == 14:
                    val = extract_int_from_string(exprun.name)
                    if val is not None:
                        experun_dirs.append((val, exprun))
                    else:
                        pass 
                        # print(f"Skipping {exprun.name!r} — no integer found.")

            # Sort by extracted integer value
            experun_dirs.sort(key=lambda x: x[0])

            # Upload in sorted order
            for _, exprun in experun_dirs:
                resp = results_upload(
                    hashID=subfolder.name,
                    runID=exprun.name,
                    data_folder=data_folder
                )
                resp["hashID"] = subfolder.name
                resp_list.append(resp)

                # time.sleep(0.1)
    return resp_list
    # print_table(resp_list)


def results_list(
    hashID: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all results rows that share the same hashID.

    Returns a list of dicts, newest first:
      {
        "name": str,
        "run_id": Optional[str],  # NEW
        "notes": Optional[str],
        "created_at": str,
      }
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/results/list"

    r = requests.get(
        url,
        params={"hashID": hashID},
        headers=_auth_headers(api_token),
        timeout=120
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Results list failed ({r.status_code}): {r.text}")
    return r.json().get("items", [])



def results_download(
    hashID: str,
    runID: str,
    output_folder: str,
    name: Optional[str] = "experiment_group",
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Tuple[Optional[str], str, str, Optional[str], bytes]:
    """
    Download the most recent result matching (hashID, name, runID),
    create <output_folder>/<hashID>/<runID>, and unzip the archive there.

    Behaviour:
      - Target dir: <output_folder>/<hashID>/<runID>
      - If that directory already exists:
            prints "experiment data exists, skipping download"
            returns (None, "", "", None, b"")
      - Otherwise:
            downloads, unzips into that directory, and returns
            (notes, filename, created_at, run_id, data_bytes)

    Returns:
        Tuple of (notes, filename, created_at, run_id, data_bytes):
          - notes (Optional[str]): Notes saved with the record.
          - filename (str): Original ZIP filename from the server.
          - created_at (str): UTC datetime string for the DB entry.
          - run_id (Optional[str]): Run ID returned by the server.
          - data_bytes (bytes): Raw ZIP file contents.
    """

    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/results/download"

    if not runID:
        raise ValueError("runID must be provided and non-empty.")

    # Target directory: <output_folder>/<hashID>/<runID>
    target_dir = Path(output_folder) / hashID / runID

    # If data already exists locally, skip download
    if target_dir.exists():
        # print("experiment data exists, skipping download")
        return (None, "", "", None, b"")

    # Request from server
    payload: Dict[str, Any] = {
        "hashID": hashID,
        "name": name,
        "runID": runID,
    }

    r = requests.post(
        url,
        json=payload,
        headers=_auth_headers(api_token),
        timeout=300,
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"Download failed ({r.status_code}): {r.text}")

    resp = r.json()

    notes = resp.get("notes")
    filename = resp["filename"]
    created_at = resp["created_at"]
    run_id = resp.get("run_id")
    data_bytes = base64.b64decode(resp["data_b64"])

    # Create folder and unzip there
    unzip_bytes_to_folder(data_bytes, str(target_dir))
    # print ("experiment data downloaded")
    return (notes, filename, created_at, run_id, data_bytes)



def set_best_run(
    calibrationHashID: str,
    runID: str,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark a (calibrationHashID, runID) pair as the current best run.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/set"

    payload = {
        "calibrationHashID": calibrationHashID,
        "runID": runID,
    }

    r = requests.post(
        url,
        json=payload,
        headers=_auth_headers(api_token),
        timeout=60,
    )

    if r.status_code >= 400:
        raise requests.HTTPError(f"set_best_run failed ({r.status_code}): {r.text}")

    return r.json()

def get_best_run(
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Returns (calibration_hash_id, run_id, created_at)
    from the most recently inserted best run.
    """
    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/get"

    r = requests.get(
        url,
        headers=_auth_headers(api_token),
        timeout=60,
    )

    if r.status_code >= 400:
        raise requests.HTTPError(f"get_best_run failed ({r.status_code}): {r.text}")

    payload = r.json()
    if payload.get("status") != "ok":
        raise requests.HTTPError(f"Server error: {payload}")

    return (
        payload["calibration_hash_id"],
        payload["run_id"],
        payload["created_at"],
    )




def get_best_n_runs(
    n: int,
    server_url: Optional[str] = None,
    api_token: Optional[str] = None,
) -> List[Tuple[str, str, str]]:
    """
    Get up to `n` previous best runs.

    Returns a list of tuples:
        [
          (calibration_hash_id, run_id, created_at),
          ...
        ]
    ordered from newest (most recent best run) to oldest,
    up to the requested limit `n`.
    """
    if n <= 0:
        raise ValueError("n must be a positive integer")

    server_url, api_token = _get_defaults(server_url, api_token)
    url = server_url + "/bestruns/list"

    r = requests.get(
        url,
        params={"limit": n},
        headers=_auth_headers(api_token),
        timeout=60,
    )
    if r.status_code >= 400:
        raise requests.HTTPError(f"get_best_n_runs failed ({r.status_code}): {r.text}")

    payload = r.json()
    if payload.get("status") != "ok":
        raise requests.HTTPError(f"Server error in get_best_n_runs: {payload}")

    items = payload.get("items", [])
    result: List[Tuple[str, str, str]] = []
    for it in items:
        result.append(
            (
                str(it["calibration_hash_id"]),
                str(it["run_id"]),
                str(it["created_at"]),
            )
        )
    return result

def unzip_bytes_to_folder(zip_bytes: bytes, target_folder: str) -> None:
    """
    Unzip in-memory ZIP data into a target folder.

    Args:
        zip_bytes: Raw ZIP file bytes.
        target_folder: Destination folder to extract into.
    """
    os.makedirs(target_folder, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(path=target_folder)

def print_table(data):
    print(tabulate(data, headers="keys", tablefmt="grid"))

    
def test():
    print ("import works!")
    