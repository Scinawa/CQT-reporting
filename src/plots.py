import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import networkx as nx
import numpy as np
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
from pathlib import Path
import json
import os
import ast
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt


from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import itertools


# def prepare_grid_coupler(
#     max_number,
#     data_dir="data/DEMODATA",
#     baseline_dir="data/DEMODATA",
#     output_path="build/",
# ):
#     """
#     Prepare the grid for the report.
#     Returns a list of dicts with 'plot' and 'baseline' keys for Jinja template.
#     """
#     plot_grid = []
#     for i in range(max_number):
#         plot_path = plot_swap_coupler(
#             qubit_number=i, data_dir=data_dir, output_path=output_path
#         )
#         baseline_path = plot_swap_coupler(
#             qubit_number=i, data_dir=baseline_dir, output_path=output_path
#         )
#         plot_grid.append(
#             {
#                 "plot": plot_path,
#                 "baseline": baseline_path,
#             }
#         )
#     return plot_grid


# def prepare_grid_chevron_swap_coupler(
#     max_number,
#     data_dir="data/DEMODATA",
#     baseline_dir="data/DEMODATA",
#     output_path="build/",
# ):
#     """
#     Prepare the grid for chevron swap coupler plots for the report.
#     Returns a list of dicts with 'plot' and 'baseline' keys for Jinja template.
#     """
#     plot_grid = []
#     for i in range(max_number):
#         plot_path = plot_chevron_swap_coupler(
#             qubit_number=i, data_dir=data_dir, output_path=output_path
#         )
#         baseline_path = plot_chevron_swap_coupler(
#             qubit_number=i, data_dir=baseline_dir, output_path=output_path
#         )
#         plot_grid.append(
#             {
#                 "plot": plot_path,
#                 "baseline": baseline_path,
#             }
#         )
#     return plot_grid


def plot_fidelity_graph(
    raw_data_single,
    raw_data_two,
    experiment_name,
    connectivity,
    pos,
    output_path="build/",
):
    """
    Generates a fidelity graph for the given experiment.
    """

    # temporary fix for demo data
    # results_demo_json_path = "data" / Path(experiment_name) / f"fidelity2qb.json"
    # with open(results_demo_json_path, "r") as f:
    #     results_tmp = json.load(f)
    # # this will be changed because of MLK - beware of stringescape issues
    # fidelities_2qb = results_tmp.get('"fidelities_2qb"', {})

    # Load results for the main path
    # results_json_path = "data" / Path(experiment_name) / "data/rb-0/results.json"

    with open(raw_data_single, "r") as f:
        results_single = json.load(f)
    with open(raw_data_two, "r") as f:
        results_two = json.load(f)

    # Extract rb_fidelity from the new structure
    single_qubits = results_single.get("single_qubits", {})
    fidelities = {}
    for qubit_id, qubit_data in single_qubits.items():
        rb_fidelity = qubit_data.get("rb_fidelity", [0, 0])
        fidelities[qubit_id] = rb_fidelity[0] if rb_fidelity else 0

    # Set missing keys to 0 for all qubits 0-19
    fidelities.update({str(qn): 0 for qn in range(20) if str(qn) not in fidelities})

    # Create 2-qubit fidelities dictionary with tuple keys and LaTeX formatted strings
    fidelities_2qb = {}
    # Keep only keys different from "best_qubits"
    two_qubits = {k: v for k, v in results_two.items() if k != "best_qubits"}

    for pair_string, fidelity_value in two_qubits.items():
        # Parse the pair string "(0, 1)" into tuple (0, 1)
        try:
            # Remove parentheses and split by comma
            clean_string = pair_string.strip("()")
            pair_parts = clean_string.split(", ")
            if len(pair_parts) == 2:
                a, b = int(pair_parts[0]), int(pair_parts[1])
                pair = (a, b)

                # The value is already a fidelity (not a list)
                if isinstance(fidelity_value, (int, float)):
                    mu = fidelity_value * 100  # Convert to percentage

                    # For single values, we don't have error, so use a placeholder or omit
                    # Truncate to 2 significant digits
                    mu_truncated = float(f"{mu:.2g}")

                    # Create LaTeX formatted string without error
                    fidelities_2qb[pair] = rf"${mu_truncated:.1f}$"
                    # Also add the reverse pair for undirected edges
                    fidelities_2qb[(b, a)] = rf"${mu_truncated:.1f}$"
        except (ValueError, IndexError):
            continue

    labels = {
        a: f"Q{a}\n{np.round(fidelities[str(a)] * 100, decimals=2)}" for a in range(20)
    }

    g = nx.Graph()
    cmap = plt.get_cmap("viridis")
    array = np.array(list(fidelities.values())) * 100
    node_color = [
        (
            plt.cm.viridis((value * 100 - min(array)) / (max(array) - min(array)))
            if value > 0.8
            else "grey"
        )
        for value in list(fidelities.values())
    ]
    levels = MaxNLocator(nbins=100).tick_values(min(array), max(array))
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

    g.add_nodes_from(list(range(20)))
    g.add_edges_from(connectivity)
    nx.draw_networkx_edges(g, pos, edge_color="black", width=5)
    nx.draw_networkx_nodes(g, pos, node_size=800, linewidths=5, node_color=node_color)
    nx.draw_networkx_labels(
        g,
        pos,
        labels=labels,
        font_color="r",
        alpha=0.6,
        font_size=8,
        font_weight="bold",
    )
    # print(connectivity)

    try:
        nx.draw_networkx_edge_labels(
            g,
            pos,
            edge_labels={
                (a, b): fidelities_2qb.get((a, b), "-") for a, b in connectivity
            },
            font_color="black",
            font_size=8,
            font_weight="bold",
        )
    except Exception as e:
        print(f"Warning: could not draw edge labels: {e}")

    ax = plt.gca()
    # Place colorbar below the plot
    cbar = plt.colorbar(
        plt.cm.ScalarMappable(norm=norm, cmap=cmap),
        ax=ax,
        orientation="horizontal",
        pad=0.1,
        fraction=0.05,
        aspect=40,  # Make the colorbar longer
        shrink=0.8,  # Adjust shrink to make it visually longer
    )
    cbar.set_label("1Q Fidelity")
    plt.box(False)
    plt.tight_layout()
    filename = "fidelities.pdf"
    os.makedirs(output_path, exist_ok=True)
    full_path = output_path + experiment_name + "_" + filename
    plt.savefig(full_path)
    plt.close()

    return full_path


# def plot_fidelity_graph(
#     raw_data, experiment_name, connectivity, pos, output_path="build/"
# ):
#     """
#     Generates a fidelity graph for the given experiment.
#     """

#     # temporary fix for demo data
#     # results_demo_json_path = "data" / Path(experiment_name) / f"fidelity2qb.json"
#     # with open(results_demo_json_path, "r") as f:
#     #     results_tmp = json.load(f)
#     # # this will be changed because of MLK - beware of stringescape issues
#     # fidelities_2qb = results_tmp.get('"fidelities_2qb"', {})

#     # Load results for the main path
#     # results_json_path = "data" / Path(experiment_name) / "data/rb-0/results.json"

#     with open(raw_data, "r") as f:
#         results = json.load(f)

#     # Extract rb_fidelity from the new structure
#     single_qubits = results.get("single_qubits", {})
#     fidelities = {}
#     for qubit_id, qubit_data in single_qubits.items():
#         rb_fidelity = qubit_data.get("rb_fidelity", [0, 0])
#         fidelities[qubit_id] = rb_fidelity[0] if rb_fidelity else 0

#     # Set missing keys to 0 for all qubits 0-19
#     fidelities.update({str(qn): 0 for qn in range(20) if str(qn) not in fidelities})

#     # Create 2-qubit fidelities dictionary with tuple keys and LaTeX formatted strings
#     fidelities_2qb = {}
#     two_qubits = results.get("two_qubits", {})

#     for pair_string, qubit_data in two_qubits.items():
#         # Parse the pair string "4-9" into tuple (4, 9)
#         pair_parts = pair_string.split("-")
#         if len(pair_parts) == 2:
#             try:
#                 a, b = int(pair_parts[0]), int(pair_parts[1])
#                 pair = (a, b)

#                 rb_fidelity = qubit_data.get("rb_fidelity", [0, 0])
#                 if rb_fidelity and len(rb_fidelity) >= 2:
#                     mu = rb_fidelity[0] * 100  # Convert to percentage
#                     sigma = rb_fidelity[1] * 100  # Convert to percentage

#                     # Truncate to 2 significant digits
#                     mu_truncated = float(f"{mu:.2g}")
#                     sigma_truncated = float(f"{sigma:.2g}")

#                     # Create LaTeX formatted string
#                     fidelities_2qb[pair] = (
#                         rf"${mu_truncated:.1f} \pm {sigma_truncated:.1f}$"
#                     )
#                     # Also add the reverse pair for undirected edges
#                     fidelities_2qb[(b, a)] = (
#                         rf"${mu_truncated:.1f} \pm {sigma_truncated:.1f}$"
#                     )
#             except (ValueError, IndexError):
#                 continue

#     labels = {
#         a: f"Q{a}\n{np.round(fidelities[str(a)] * 100, decimals=2)}" for a in range(20)
#     }

#     g = nx.Graph()
#     cmap = plt.get_cmap("viridis")
#     array = np.array(list(fidelities.values())) * 100
#     node_color = [
#         (
#             plt.cm.viridis((value * 100 - min(array)) / (max(array) - min(array)))
#             if value > 0.8
#             else "grey"
#         )
#         for value in list(fidelities.values())
#     ]
#     levels = MaxNLocator(nbins=100).tick_values(min(array), max(array))
#     norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

#     g.add_nodes_from(list(range(20)))
#     g.add_edges_from(connectivity)
#     nx.draw_networkx_edges(g, pos, edge_color="black", width=5)
#     nx.draw_networkx_nodes(g, pos, node_size=800, linewidths=5, node_color=node_color)
#     nx.draw_networkx_labels(
#         g,
#         pos,
#         labels=labels,
#         font_color="r",
#         alpha=0.6,
#         font_size=8,
#         font_weight="bold",
#     )
#     # print(connectivity)
#     # import pdb

#     # pdb.set_trace()
#     try:
#         nx.draw_networkx_edge_labels(
#             g,
#             pos,
#             edge_labels={
#                 (a, b): fidelities_2qb.get((a, b), "-") for a, b in connectivity
#             },
#             font_color="black",
#             font_size=8,
#             font_weight="bold",
#         )
#     except Exception as e:
#         print(f"Warning: could not draw edge labels: {e}")

#     ax = plt.gca()
#     # Place colorbar below the plot
#     cbar = plt.colorbar(
#         plt.cm.ScalarMappable(norm=norm, cmap=cmap),
#         ax=ax,
#         orientation="horizontal",
#         pad=0.1,
#         fraction=0.05,
#         aspect=40,  # Make the colorbar longer
#         shrink=0.8,  # Adjust shrink to make it visually longer
#     )
#     cbar.set_label("1Q Fidelity")
#     plt.box(False)
#     plt.tight_layout()
#     filename = "fidelities.pdf"
#     full_path = output_path + experiment_name + "_" + filename
#     plt.savefig(full_path)
#     plt.close()
#     return full_path


def plot_swap_coupler(qubit_number=0, data_dir="data/DEMODATA", output_path="build/"):
    """
    Plots the swap coupler data for a given qubit index.

    Args:
        QUBIT (int): Qubit index (0-based).
        data_dir (str): Directory containing the JSON data file.
    """

    file_path = os.path.join(data_dir, f"swap_q{qubit_number + 1}_coupler.json")
    with open(file_path) as r:
        data = json.load(r)

    x = np.array(data["x"])
    y = np.array(data["y"])
    res = np.array(data["data"]).transpose() * 1e6

    fig, ax = plt.subplots()
    levels = MaxNLocator(nbins=100).tick_values(res.min(), res.max())
    cmap = plt.get_cmap("inferno")
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
    im = ax.imshow(
        res,
        cmap=cmap,
        norm=norm,
        extent=(x[0], x[-1], y[-1], y[0]),
        aspect="auto",
        origin="upper",
        interpolation="none",
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Transmission [ADC arb. units]")
    ax.axhline(0.12, label="Coupler Sweetspot", color="blue", linestyle="dashed")
    ax.set_ylabel("Coupler Amplitude [arb. units]")
    ax.set_xlabel("SWAP Length [ns]")
    fig.tight_layout()
    output_path = os.path.join(
        data_dir, f"chevron_swap_q{qubit_number + 1}_coupler.pdf"
    )
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    return output_path


def plot_chevron_swap_coupler(
    qubit_number=0, data_dir="data/DEMODATA/", output_path="build/"
):
    """
    Chevron plot for the SWAP coupler data.

    Args:
        qubit_number (int, optional): _description_. Defaults to 0.
        data_dir (str, optional): _description_. Defaults to "./data/".
        output_path (str, optional): _description_. Defaults to "build/".
    """

    # Use data_dir for the file path
    file_path = os.path.join(data_dir, f"swap_q{qubit_number + 1}.json")
    with open(file_path) as r:
        data = json.load(r)

    x = np.array(data["x"])
    y = np.array(data["y"])
    res = np.array(data["data"]).transpose() * 1e6

    fig, ax = plt.subplots()
    levels = MaxNLocator(nbins=100).tick_values(res.min(), res.max())
    cmap = plt.get_cmap("inferno")
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
    im = ax.imshow(
        res,
        cmap=cmap,
        norm=norm,
        extent=(x[0], x[-1], y[-1], y[0]),
        aspect="auto",
        origin="upper",
        interpolation="none",
    )
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Transmission [ADC arb. units]")
    ax.set_ylabel("SWAP Amplitude [arb. units]")
    ax.set_xlabel("SWAP Length [ns]")
    ax.set_title(f"Q13")
    fig.tight_layout()
    output_path = os.path.join(output_path, f"chevron_swap_q{qubit_number + 1}.pdf")
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    return output_path


def prepare_grid_t1_plts(max_number, data_dir, output_path="build/"):
    """
    Prepare a grid of dummy T1 decay plots for the report.
    Returns a list of dicts with 'plot' and 'plot_baseline' keys for Jinja template.
    """
    plot_grid = []
    for i in range(max_number):
        plot_path = plot_t1_decay(
            qubit_number=i, data_dir=data_dir, output_path=output_path
        )
        plot_baseline_path = plot_t1_decay(
            qubit_number=i,
            data_dir=data_dir,
            output_path=output_path,
            suffix="_baseline",
        )
        plot_grid.append({"plot": plot_path, "plot_baseline": plot_baseline_path})
    return plot_grid


def plot_t1_decay(qubit_number, data_dir, output_path="build/", suffix=""):
    """
    Create a dummy T1 decay plot: exponential decay from 1 to 0.
    X axis: milliseconds, Y axis: T1
    """

    x = np.linspace(0, 10, 100)
    y = np.exp(-x / 3)  # Arbitrary decay constant for mockup
    plt.figure()
    plt.plot(x, y, label=f"Qubit {qubit_number}")
    plt.xlabel("milliseconds")
    plt.ylabel("T1")
    plt.title(f"T1 Decay Qubit {qubit_number}{suffix}")
    plt.ylim(0, 1.05)
    plt.xlim(0, 10)
    plt.legend()
    plt.tight_layout()
    filename = f"t1_{qubit_number}{suffix}.pdf"
    full_path = os.path.join(output_path, filename)
    plt.savefig(full_path)
    plt.close()
    return full_path


def mermin_plot(raw_data, expname, output_path="build/"):
    with open(raw_data) as r:
        raw = json.load(r)

    # Support both list and dict formats
    x_raw = raw.get("x", {})
    y_raw = raw.get("y", {})

    number_of_qubits_ = [k for k in x_raw.keys()][0]
    number_of_qubits = len(ast.literal_eval(number_of_qubits_))

    series = []
    if isinstance(x_raw, dict) and isinstance(y_raw, dict):
        # Collect common keys and build series list
        for k in y_raw.keys():
            if k in x_raw and isinstance(x_raw[k], list) and isinstance(y_raw[k], list):
                try:
                    xs = np.array(x_raw[k], dtype=float)
                    ys = np.array(y_raw[k], dtype=float)
                    series.append((k, xs, ys))
                except Exception:
                    continue
    else:
        # Fallback to simple list arrays
        try:
            xs = np.array(x_raw, dtype=float)
            ys = np.array(y_raw, dtype=float)
            series.append(("series", xs, ys))
        except Exception:
            series = []

    if not series:
        raise ValueError(f"No valid Mermin data to plot from {raw_data}")

    os.makedirs(output_path, exist_ok=True)
    plt.figure()

    # Plot all series and track global max
    global_max = None
    for label, xs, ys in series:
        plt.plot(xs / np.pi * 180.0, ys, label=label if len(series) > 1 else None)
        candidate = ys[np.nanargmax(np.abs(ys))]
        if global_max is None or np.abs(candidate) > np.abs(global_max):
            global_max = candidate

    classical_bound = 2 ** (number_of_qubits // 2)

    quantum_bound = 2 ** ((number_of_qubits - 1) / 2) * (2 ** (number_of_qubits // 2))

    plt.axhline(
        classical_bound, color="k", linestyle="dashed", label="Local Realism Bound"
    )
    plt.axhline(-classical_bound, color="k", linestyle="dashed")
    plt.axhline(quantum_bound, color="red", linestyle="dashed", label="Quantum Bound")
    plt.axhline(-quantum_bound, color="red", linestyle="dashed")

    plt.xlabel(r"$\theta$ [degrees]")
    plt.ylabel("Result")
    plt.grid()
    if len(series) > 1:
        plt.legend()
    plt.title(f"Mermin Inequality [{number_of_qubits} qubits]\nMax: {global_max}")
    plt.tight_layout()

    filename = f"{expname}_mermin.png"
    full_path = os.path.join(output_path, filename)
    plt.savefig(full_path)
    plt.close()
    return full_path


def plot_reuploading(x, target, predictions=None, err=None, title="plot", outdir="."):
    """Plot target function and, optionally, the predictions of our model."""
    # flatten everything to 1D
    x = np.asarray(x).reshape(-1)
    target = np.asarray(target).reshape(-1)
    if predictions is not None:
        predictions = np.asarray(predictions).reshape(-1)
    if err is not None:
        err = np.asarray(err).reshape(-1)

    plt.figure(figsize=(4, 4 * 6 / 8), dpi=120)
    plt.plot(
        x,
        target,
        marker="o",
        markersize=7,
        alpha=1,
        label="Targets",
        ls="-",
        markeredgecolor="black",
        color="red",
    )
    if predictions is not None:
        plt.plot(
            x,
            predictions,
            marker="o",
            markersize=7,
            alpha=1,
            label="Predictions",
            ls="-",
            markeredgecolor="black",
            color="blue",
        )
    if predictions is not None and err is not None:
        plt.fill_between(
            x, predictions - err, predictions + err, alpha=0.3, color="blue"
        )
    plt.xlabel(r"$x$")
    plt.ylabel(r"$f(x)$")
    plt.legend()
    os.makedirs(outdir, exist_ok=True)
    plt.savefig(os.path.join(outdir, f"{title}.pdf"), dpi=300, bbox_inches="tight")
    plt.close()
    return os.path.join(outdir, f"{title}.pdf")


def plot_grover(raw_data, expname, output_path="build/"):
    """
    Plot Grover's algorithm results as a histogram of measured bitstrings.
    """
    # Load data from JSON file
    with open(raw_data, "r") as f:
        data = json.load(f)

    # Extract frequencies for the first (and only) key in 'frequencies'
    frequencies = data["plotparameters"]["frequencies"]
    key = next(iter(frequencies))
    freq_dict = frequencies[key]

    # Use evenly spaced numeric positions and set bitstrings as tick labels to avoid gaps/warnings
    labels = list(freq_dict.keys())
    if all(isinstance(k, str) and set(k) <= {"0", "1"} for k in labels):
        labels = sorted(labels, key=lambda s: int(s, 2))
    x = np.arange(len(labels))
    counts = [freq_dict[k] for k in labels]
    tick_labels = [str(k) for k in labels]

    plt.figure()
    plt.bar(x, counts, color="skyblue", edgecolor="black")
    plt.xlabel("Bitstring")
    plt.ylabel("Counts")
    plt.title("Grover's Algorithm Measurement Histogram")
    plt.xticks(x, tick_labels, rotation=45, ha="right")
    plt.tight_layout()

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, f"{expname}_results.pdf")
    plt.savefig(out_file)
    plt.close()
    return out_file


# def plot_qft(raw_data, expname, output_path="../build/"):
#     """
#     Plot QFT algorithm results on different triples as fidelities.
#     """
#     # Load data from JSON file
#     with open(raw_data, "r") as f:
#         data = json.load(f)

#     # Extract frequencies for the first (and only) key in 'frequencies'
#     fidelities = data["plotparameters"]["fidelities"]
#     qubits_lists = data["plotparameters"]["qubits_lists"]

#     # Ensure bitstrings are strings for plotting
#     bitstrings = [str(bs) for bs in qubits_lists]

#     plt.figure()
#     plt.plot(bitstrings, fidelities, color="skyblue", linestyle="None", marker="x")
#     # plt.plot(bitstrings, np.ones_like(fidelities), color="r")
#     plt.xticks(rotation=90)
#     plt.xlabel("Qubits Set")
#     plt.ylabel("Fidelity")
#     plt.title("QFT's Fidelity on Different set of qubits")
#     plt.tight_layout()

#     os.makedirs(output_path, exist_ok=True)
#     out_file = os.path.join(output_path, f"{expname}_results.pdf")
#     plt.savefig(out_file)
#     plt.close()
#     return out_file

def plot_qft(raw_data, expname, output_path="../build/"):
    """
    Plot the results of a Quantum Fourier Transform (QFT) experiment as a histogram.
    Args:
        raw_data (str): Path to the JSON file containing the QFT results.
        output_path (str): Directory to save the output plot.
    Returns:
        str: Path to the saved plot file.
    """
    # Data load
    with open(raw_data, "r") as f:
        data = json.load(f)
    qubits_list = data["edges"]
    dataplot = data["frequencies"].values()
    # n_shots = data["nshots"]
    qubits_set = set(sum(qubits_list, []))
    n_qubits = len(qubits_set)                         # number of qubits
    all_bitstrings = [format(i, f"0{n_qubits}b") for i in range(2**n_qubits)]
    os.makedirs(output_path, exist_ok=True)
    # Plot
    plt.bar(all_bitstrings, dataplot, color="skyblue", edgecolor="black")
    plt.title(f"QFT Manually Transpiled on with shots. \n Execution on edges {qubits_list}")
    plt.xlabel("States")
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Counts")
    plt.legend()
    plt.tight_layout()
    # plt.show()
    # Save plot
    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, f"{expname}_results.pdf")
    plt.savefig(out_file)
    plt.close()
    return out_file


def plot_ghz(raw_data, experiment_name, output_path="../build/"):
    """
    Plot GHZ results as a histogram of measured bitstrings.
    Expects a JSON with keys:
      - success_rate
      - plotparameters: { frequencies: { <bitstring>: count, ... } }
    """
    with open(raw_data, "r") as f:
        data = json.load(f)

    freq_dict = data.get("plotparameters", {}).get("frequencies", {})
    success_rate = data.get("success_rate", None)

    # Ensure bitstrings are strings for plotting
    bitstrings = [str(b) for b in freq_dict.keys()]
    counts = [freq_dict[b] for b in freq_dict]

    plt.figure()
    plt.bar(bitstrings, counts, color="mediumseagreen", edgecolor="black")
    plt.xlabel("Bitstring")
    plt.ylabel("Counts")
    title = "GHZ State Measurement Histogram"
    if success_rate is not None:
        title += f" (Success: {success_rate:.3f})"
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, f"{experiment_name}_ghz_results.pdf")
    plt.savefig(out_file)
    plt.close()
    return out_file


def plot_amplitude_encoding(raw_data, expname, output_path="build/"):
    """
    Plot Amplitude Encoding algorithm results as a histogram of measured
    bitstrings, together with the expected outcome.
    """
    # Load data from JSON file
    with open(raw_data, "r") as f:
        data = json.load(f)

    # Extract frequencies for the first (and only) key in 'frequencies'
    frequencies = data["plotparameters"]["frequencies"]
    input_vector = data["input_vector"]
    norm_vector = input_vector / np.linalg.norm(input_vector)

    # Ensure bitstrings are strings for plotting
    bitstrings = [str(bs) for bs in frequencies.keys()]
    counts = [frequencies[bs] for bs in frequencies.keys()]

    plt.figure()
    plt.bar(bitstrings, counts, color="skyblue", edgecolor="black")
    plt.plot(norm_vector**2 * np.sum(counts), "-x", c="red")
    plt.xlabel("Bitstring")
    plt.ylabel("Counts")
    plt.title("Amplitude Encoding Algorithm Measurement Histogram")
    plt.tight_layout()

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, f"{expname}_results.pdf")
    plt.savefig(out_file)
    plt.close()
    return out_file


def plot_reuploading_classifier(raw_data, exp_name, output_path="../build/"):
    # Retrieve relevant data
    with open(raw_data, "r") as f:
        data_json = json.load(f)

    # import pdb

    # pdb.set_trace()

    train_x = np.array(data_json["x_train"])
    train_pred_errors = np.array(data_json["train_pred_errors"])
    train_pred_errors = np.transpose(
        np.array([train_x[ind] for ind in train_pred_errors])
    )
    train_y = np.array(data_json["train_predictions"])
    test_x = np.array(data_json["x_test"])
    test_pred_errors = np.array(data_json["test_pred_errors"])
    test_pred_errors = np.transpose(np.array([test_x[ind] for ind in test_pred_errors]))
    test_y = np.array(data_json["test_predictions"])
    loss_history = data_json["loss_history"]
    train_acc = data_json["train_accuracy"]
    test_acc = data_json["test_accuracy"]

    if loss_history:
        fig = plt.figure(figsize=(8, 6), dpi=120)
        gs = fig.add_gridspec(2, 2, height_ratios=[2, 1])  # 2 rows, 2 columns
    else:
        fig = plt.figure(figsize=(8, 4), dpi=120)
        gs = fig.add_gridspec(1, 2)  # 1 row, 2 columns

    # Train plot (top-left)
    ax_train = fig.add_subplot(gs[0, 0])
    for label in np.unique(train_y):
        data_label = np.transpose(train_x[np.where(train_y == label)])
        ax_train.scatter(data_label[0], data_label[1])
    ax_train.scatter(
        train_pred_errors[0], train_pred_errors[1], marker="x", color="black"
    )
    ax_train.set_title(f"Train predictions: {train_acc} accuracy")
    ax_train.set_xlabel(r"$x$")
    ax_train.set_ylabel(r"$y$")
    circle_train = plt.Circle(
        (0, 0), np.sqrt(2 / np.pi), edgecolor="k", linestyle="--", fill=False
    )
    ax_train.add_patch(circle_train)

    # Test plot (top-right)
    ax_test = fig.add_subplot(gs[0, 1])
    for label in np.unique(test_y):
        data_label = np.transpose(test_x[np.where(test_y == label)])
        ax_test.scatter(data_label[0], data_label[1])
    ax_test.scatter(test_pred_errors[0], test_pred_errors[1], marker="x", color="black")
    ax_test.set_title(f"Test predictions: {test_acc} accuracy")
    ax_test.set_xlabel(r"$x$")
    ax_test.set_ylabel(r"$y$")
    circle_test = plt.Circle(
        (0, 0), np.sqrt(2 / np.pi), edgecolor="k", linestyle="--", fill=False
    )
    ax_test.add_patch(circle_test)

    if loss_history:
        # Loss plot (bottom row spanning both columns)
        ax_loss = fig.add_subplot(gs[1, :])
        ax_loss.plot(loss_history)
        ax_loss.set_title("Loss plot")
        ax_loss.set_xlabel(r"$Iteration$")
        ax_loss.set_ylabel(r"$Loss$")

    plt.tight_layout()
    os.makedirs(output_path, exist_ok=True)
    fig.savefig(
        os.path.join(output_path, f"reuploading_classifier_results_{exp_name}.pdf"),
        bbox_inches="tight",
        dpi=300,
    )
    plt.close(fig)
    return os.path.join(output_path, f"reuploading_classifier_results_{exp_name}.pdf")


def do_plot_reuploading(raw_data, expname, output_path="build/"):
    """
    Generate reuploading plots for each epoch and a final summary plot using data from the results JSON file.

    Args:
        results_file (str): Path to the JSON file containing reuploading results.
    """
    with open(raw_data, "r") as f:
        results = json.load(f)

    output_dir = output_path

    # Generate a plot for each epoch
    for epoch_data in results["epoch_data"]:
        epoch = epoch_data["epoch"]
        x_train = np.array(epoch_data["x_train"])
        y_train = np.array(epoch_data["y_train"])
        predictions = np.array(epoch_data["predictions"])

        plot_reuploading(
            x=x_train,
            target=y_train,
            predictions=predictions,
            title=f"epoch_{epoch:03d}",
            outdir=output_dir,
        )

    # Generate the final summary plot
    x_train = np.array(results["epoch_data"][-1]["x_train"])
    y_train = np.array(results["epoch_data"][-1]["y_train"])
    median_pred = np.array(results["median_predictions"])
    mad_pred = np.array(results["mad_predictions"])

    plot_reuploading(
        x=x_train,
        target=y_train,
        predictions=median_pred,
        err=mad_pred,
        title=f"final_plot_{expname}",
        outdir=output_dir,
    )

    return os.path.join(output_dir, f"plot_reuploading_{expname}.pdf")


def plot_process_tomography(calid, runid, output_path="build/"):
    """
    Plot process tomography matrices for a given experiment/expname.

    Args:
        expname (str): Experiment name to include in the output filename.
        output_path (str): Directory to save the output plot.
    Returns:
        str: Path to saved PDF file.
    """

    repo_root = os.path.dirname(os.path.dirname(__file__))  # ../ from src/
    folder_path = os.path.join(
        repo_root, "data", calid, runid, "process_tomography", "matrices"
    )
    npy_files = np.sort([f for f in os.listdir(folder_path) if f.endswith(".npy")])

    fig, ax = plt.subplots(len(npy_files), 1, figsize=[len(npy_files) * 5, 15], dpi=300)

    # If only one subplot, wrap it in a list for consistency
    if len(npy_files) == 1:
        ax = [ax]

    for idx, file_name in enumerate(npy_files):
        full_path = os.path.join(folder_path, file_name)
        arr = np.load(full_path)

        # Define labels depending on matrix shape
        if arr.shape == (4, 4):
            labels = ["I", "X", "Y", "Z"]
            fontsize = 10
        elif arr.shape == (16, 16):
            single_labels = ["I", "X", "Y", "Z"]
            labels = [a + b for a, b in itertools.product(single_labels, repeat=2)]
            fontsize = 8
        else:
            labels = []
            fontsize = 10

        ax[idx].imshow(np.real(arr), cmap="coolwarm", vmin=-1, vmax=1)
        ax[idx].set_xticks(range(len(labels)))
        ax[idx].set_yticks(range(len(labels)))
        ax[idx].set_xticklabels(labels, fontsize=fontsize)
        ax[idx].set_yticklabels(labels, fontsize=fontsize)
        title = file_name.removeprefix("gate_").replace(".npy", f"_{calid}")
        ax[idx].set_title(title)

        # Add colorbar beside subplots
        im = ax[idx].imshow(np.real(arr), cmap="coolwarm", vmin=-1, vmax=1)
        cbar = fig.colorbar(
            im, ax=ax[idx], orientation="vertical", fraction=0.05, pad=0.01
        )

    plt.tight_layout()

    os.makedirs(output_path, exist_ok=True)
    out_file = os.path.join(output_path, f"process_tomography_{calid}_matrices.pdf")
    plt.savefig(out_file, format="pdf", bbox_inches="tight")
    plt.close()

    # return "placeholder.png"
    return out_file


def plot_tomography(raw_data, expname, output_path="build/"):
    return "placeholder.png"


def plot_qml(raw_data, expname, output_path="build/"):

    with open(raw_data, "r") as f:
        data = json.load(f)

    qc_configurations = data.get("NQCH", {})
    noiseless_configuration = data.get("verification_ios", {})

    # Extract true and predicted labels from the dict values
    true = []
    pred = []
    noiseless = []

    for key, sample in qc_configurations.items():
        pred_label = int(sample.get("predicted_label", 0))
        is_correct = sample.get("is_correct", True)
        # Infer true label from is_correct and predicted_label
        true_label = pred_label if is_correct else 1 - pred_label
        true.append(true_label)
        pred.append(pred_label)
        # Get noiseless label from verification_ios dict
        noiseless_label = int(noiseless_configuration.get(key, {}).get("predicted_label", 0))
        noiseless.append(noiseless_label)

    true = np.array(true, dtype=int)
    pred = np.array(pred, dtype=int)
    noiseless = np.array(noiseless, dtype=int)

    # Build confusion matrices (force both classes to appear: 0,1)
    labels = [0, 1]
    cm_pred = confusion_matrix(true, pred, labels=labels)
    cm_noiseless = confusion_matrix(true, noiseless, labels=labels)

    os.makedirs(output_path, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    disp1 = ConfusionMatrixDisplay(confusion_matrix=cm_pred, display_labels=labels)
    disp1.plot(cmap="Blues", ax=axes[0], colorbar=False)
    axes[0].set_title("Prediction vs Ground Truth")

    disp2 = ConfusionMatrixDisplay(confusion_matrix=cm_noiseless, display_labels=labels)
    disp2.plot(cmap="Greens", ax=axes[1], colorbar=False)
    axes[1].set_title("Noiseless circuit vs Ground Truth")

    fig.suptitle(f"QML Confusion Matrices", fontsize=14)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    out_file = os.path.join(output_path, f"{expname}_qml_confusion_matrices.pdf")
    fig.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_file
