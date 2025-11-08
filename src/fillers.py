import argparse
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import logging
import os
import json
import numpy as np
import pdb


import matplotlib.pyplot as plt


def get_qml_accuracy(filename):

    with open(filename, "r") as f:
        results = json.load(f)

    return results["accuracy"]


def extract_description(filename):

    with open(filename, "r") as f:
        results = json.load(f)

    return results.get("description", " --- No description provided. ---")


def extract_runtime(filename):

    with open(filename, "r") as f:
        results = json.load(f)

    return results.get("runtime", " --- No runtime provided. ---")


def extract_qubits_used(filename):

    with open(filename, "r") as f:
        results = json.load(f)

    return results.get("qubits_used", " --- No ``qubits\_used'' provided. ---")


def process_commit_info(filename):
    with open(filename, "r") as f:
        results = json.load(f)

    return results


def context_plot_1(exp_name):
    """
    Generates a plot with y-axis from 0 to 1 and x-axis from 0 to 500.
    Returns the filepath of the saved image.
    """
    fig, ax = plt.subplots()
    ax.set_xlim(0, 500)
    ax.set_ylim(0, 1)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("Plot 1: what do you want?")
    # Optionally, plot a line or leave empty
    # ax.plot([], [])
    output_dir = Path("build")
    output_dir.mkdir(exist_ok=True)
    filename = f"plot_1_{exp_name}.pdf"
    filepath = output_dir / filename
    plt.savefig(filepath)
    plt.close(fig)
    return str(filepath)


def get_maximum_mermin(experiment_dir, filename):
    """
    Extracts the maximum absolute value from the Mermin results JSON file.
    Supports formats:
      - {"y": {"[0, 1, 2]": [..], ...}}
      - {"y": [..]}
    """
    results_json_path = Path(experiment_dir) / filename
    with open(results_json_path, "r") as f:
        results = json.load(f)

    y_data = results.get("y")
    if y_data is None:
        return None

    series = []
    if isinstance(y_data, dict):
        # Collect all lists of y-values from the dict
        for vals in y_data.values():
            if isinstance(vals, list):
                series.extend(vals)
    elif isinstance(y_data, list):
        series = y_data

    if not series:
        return None

    try:
        arr = np.asarray(series, dtype=float)
    except Exception as e:
        print(f"Error converting value {v}: {e}")
        # Fallback: attempt to coerce element-wise
        cleaned = []
        for v in series:
            try:
                cleaned.append(float(v))
            except Exception as e:
                print(f"Error converting value {v}: {e}")
                cleaned.append(np.nan)
        arr = np.asarray(cleaned, dtype=float)

    max_value = np.nanmax(np.abs(arr))
    return max_value


def context_version(calibration_id, version_extractor_results_path):
    """
    Get the version info from the version_extractor experiment results.json file.

    Args:
        version_extractor_results_path (str): Path to the version_extractor results.json file

    Returns:
        dict: Dictionary containing versions, device, and extraction_time
    """
    try:
        # import pdb

        # pdb.set_trace()
        with open(version_extractor_results_path, "r") as f:
            version_data = json.load(f)

        return {
            "versions": version_data.get("versions", {}),
            "device": version_data.get("device", "Unknown Device"),
            "extraction_time": version_data.get("extraction_time", "Unknown Time"),
            "calibration_id": calibration_id,
            "runcard_link": "https://link-to-runcard.com",  # Default link
        }
    except Exception as e:
        logging.warning(
            f"Error reading version data from {version_extractor_results_path}: {e}"
        )
        return {
            "versions": {},
            "device": "Unknown Device",
            "extraction_time": "Unknown Time",
            "runcard": "Unknown Device",
            "runcard_link": "https://link-to-runcard.com",
        }


def context_fidelity(experiment_dir):
    """
    Extracts the list of fidelities and error bars from the experiment results.
    Returns a list of dicts: {"fidelity": ..., "error_bars": ...}
    """
    results_json_path = Path("data") / "calibrations" / experiment_dir / "calibration.json"
    with open(results_json_path, "r") as f:
        results = json.load(f)

    # Extract rb_fidelity from the new structure
    single_qubits = results.get("single_qubits", {})
    fidelities = {}
    error_bars = {}

    for qubit_id, qubit_data in single_qubits.items():
        rb_fidelity = qubit_data.get("rb_fidelity", [0, 0])
        fidelities[qubit_id] = rb_fidelity[0] if rb_fidelity else 0
        error_bars[qubit_id] = (
            rb_fidelity[1] if rb_fidelity and len(rb_fidelity) > 1 else 0
        )

    # Set missing keys to 0 for all qubits 0-19
    fidelities.update({str(qn): 0 for qn in range(20) if str(qn) not in fidelities})
    error_bars.update({str(qn): 0 for qn in range(20) if str(qn) not in error_bars})

    # Create ordered lists for qubits 0-19
    fidelities_list = [fidelities[str(qn)] for qn in range(20)]
    error_bars_list = [error_bars[str(qn)] for qn in range(20)]

    _ = [
        {
            "qn": i,
            "fidelity": f"{f:.3g}" if isinstance(f, (float, int)) else f,
            "error_bars": f"{e:.3g}" if isinstance(e, (float, int)) else e,
        }
        for i, (f, e) in enumerate(zip(fidelities_list, error_bars_list))
    ]
    # mark the best fidelity by writing the element to \textcolor{green}{element}
    max_fidelity = np.nanmax(
        [
            float(item["fidelity"])
            for item in _
            if isinstance(item["fidelity"], (float, int))
            or (
                isinstance(item["fidelity"], str)
                and item["fidelity"].replace(".", "", 1).isdigit()
            )
        ]
    )
    # print(max_fidelity)
    _ = [
        {
            "qn": item["qn"],
            "fidelity": (
                f"\\textcolor{{green}}{{{item['fidelity']}}}"
                if (
                    np.isclose(
                        float(item["fidelity"]), max_fidelity, rtol=1e-3, atol=1e-3
                    )
                )
                else item["fidelity"]
            ),
            "error_bars": item["error_bars"],
        }
        for item in _
    ]

    # pdb.set_trace()
    # Debugging line to inspect the fidelity and error bars
    # Zip and return as list of dicts for template clarity
    return _


def get_stat_fidelity(raw_data, experiment_dir):
    """
    Returns a dictionary with average, min, max, and median fidelity for the given experiment directory.
    """

    with open(raw_data, "r") as f:
        results = json.load(f)

    fidelities = results.get('"fidelity"', {})
    # Convert dict_values to list and flatten if needed
    fidelities_list = list(fidelities.values())

    # Convert all values to float if possible
    numeric_fidelities = []
    for f in fidelities_list:
        try:
            numeric_fidelities.append(float(f))
        except (ValueError, TypeError):
            continue

    if not numeric_fidelities:
        return {"average": None, "min": None, "max": None, "median": None}

    dict_fidelities = {
        "average": f"{np.nanmean(numeric_fidelities):.3g}",
        "min": f"{np.nanmin(numeric_fidelities):.3g}",
        "max": f"{np.nanmax(numeric_fidelities):.3g}",
        "median": f"{np.nanmedian(numeric_fidelities):.3g}",
    }

    return dict_fidelities


def get_stat_t12(experiment_dir, stat_type):
    """
    Returns a dictionary with average, min, max, and median T1 for the given experiment directory.
    """
    results_json_path = Path("data") / experiment_dir / "calibration.json"
    with open(results_json_path, "r") as f:
        results = json.load(f)

    # Extract T1 values for all qubits from the "single_qubits" section
    single_qubits = results.get("single_qubits", {})
    ts_list = []
    for qubit_data in single_qubits.values():
        t1_values = qubit_data.get(stat_type, [])
        # Only consider non-null, numeric values
        for t in t1_values:
            if t is not None:
                try:
                    ts_list.append(float(t))
                except (ValueError, TypeError):
                    continue

    numeric_ts = ts_list

    if not numeric_ts:
        return {"average": None, "min": None, "max": None, "median": None}

    dict_ts = {
        "average": f"{np.nanmean(numeric_ts):.3g}",
        "min": f"{np.nanmin(numeric_ts):.3g}",
        "max": f"{np.nanmax(numeric_ts):.3g}",
        "median": f"{np.nanmedian(numeric_ts):.3g}",
    }
    return dict_ts


def get_stat_pulse_fidelity(experiment_dir):
    """
    Returns a dictionary with average, min, max, and median pulse fidelity for the given experiment directory.
    """
    results_json_path = Path("data") / experiment_dir / "data/rb-0/results.json"
    with open(results_json_path, "r") as f:
        results = json.load(f)

    pulse_fidelities = results.get('"pulse_fidelity"', {})
    # Convert dict_values to list and flatten if needed
    pulse_fidelities_list = list(pulse_fidelities.values())

    # Convert all values to float if possible
    numeric_pulse_fidelities = []
    for f in pulse_fidelities_list:
        try:
            numeric_pulse_fidelities.append(float(f))
        except (ValueError, TypeError):
            continue

    if not numeric_pulse_fidelities:
        return {"average": None, "min": None, "max": None, "median": None}

    dict_pulse_fidelities = {
        "average": f"{np.nanmean(numeric_pulse_fidelities):.3g}",
        "min": f"{np.nanmin(numeric_pulse_fidelities):.3g}",
        "max": f"{np.nanmax(numeric_pulse_fidelities):.3g}",
        "median": f"{np.nanmedian(numeric_pulse_fidelities):.3g}",
    }

    return dict_pulse_fidelities


def get_readout_fidelity(raw_data, experiment_dir):
    """
    Returns a dictionary with average, min, max, and median readout fidelity for the given experiment directory.
    """
    # results_json_path = Path("data") / experiment_dir / "calibration.json"
    with open(raw_data, "r") as f:
        results = json.load(f)

    # Extract readout fidelity from the new structure
    single_qubits = results.get("single_qubits", {})
    readout_fidelities = []

    for qubit_data in single_qubits.values():
        readout_fidelity = qubit_data.get("readout", {}).get("fidelity", None)
        if readout_fidelity is not None:
            try:
                readout_fidelities.append(float(readout_fidelity))
            except (ValueError, TypeError):
                continue

    if not readout_fidelities:
        return {"average": None, "min": None, "max": None, "median": None}

    dict_readout_fidelities = {
        "average": f"{np.nanmean(readout_fidelities):.3g}",
        "min": f"{np.nanmin(readout_fidelities):.3g}",
        "max": f"{np.nanmax(readout_fidelities):.3g}",
        "median": f"{np.nanmedian(readout_fidelities):.3g}",
    }

    return dict_readout_fidelities


def extract_best_qubits(bell_tomography_results_path):
    """
    Extract the best qubits data from bell tomography results.

    Args:
        bell_tomography_results_path (str): Path to the bell_tomography results.json file

    Returns:
        dict: Dictionary containing best qubits for k=2,3,4,5 with their fidelities
    """
    try:
        with open(bell_tomography_results_path, "r") as f:
            results = json.load(f)

        best_qubits_data = results.get("best_qubits", {})

        # Format the data for template use
        formatted_data = {}
        for k in ["2", "3", "4", "5"]:
            if k in best_qubits_data:
                qubits_list = best_qubits_data[k][0]  # First element is the qubit list
                fidelity = best_qubits_data[k][1]  # Second element is the fidelity

                # Format qubits as comma-separated string
                qubits_str = ", ".join(map(str, qubits_list))
                formatted_data[k] = {
                    "qubits": qubits_str,
                    "fidelity": f"{fidelity:.3f}",
                }
            else:
                formatted_data[k] = {"qubits": "N/A", "fidelity": "N/A"}

        return formatted_data

    except Exception as e:
        logging.warning(
            f"Error reading best qubits data from {bell_tomography_results_path}: {e}"
        )
        # Return default structure if file doesn't exist or has errors
        return {
            str(k): {"qubits": "N/A", "fidelity": "N/A"} for k in ["2", "3", "4", "5"]
        }
