import os
import logging
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import plots as pl
import fillers as fl
import config as config


def add_stat_changes(current, baseline):
    """
    Returns a dict with average, min, max, median and their changes vs baseline.
    """

    def get_change(curr, base):
        if curr is None or base is None:
            return None
        try:
            diff = float(curr) - float(base)
            if base == 0:
                return None
            percent = (diff / float(base)) * 100
            if percent > 0:
                return f"(+{percent:.2f}\\%)"
            elif percent < 0:
                return f"({percent:.2f}\\%)"
            else:
                return "-"
        except Exception:
            return None

    result = {}
    for key in ["average", "min", "max", "median"]:
        curr_val = current.get(key)
        base_val = baseline.get(key)
        result[key] = curr_val
        result[f"{key}_change"] = get_change(curr_val, base_val)
    return result


# def context_fidelity_statistics(context, cfg):

#     return context


def context_pulse_fidelity_statistics(context, cfg):
    """Prepare pulse fidelity statistics for both experiments."""
    stat_pulse_fidelity_left = fl.get_stat_pulse_fidelity(
        cfg.calibration_left + "/sinq20"
    )
    stat_pulse_fidelity_right = fl.get_stat_pulse_fidelity(
        cfg.calibration_right + "/sinq20"
    )

    # this add statistical improvements
    stat_pulse_fidelity_with_improvement = add_stat_changes(
        stat_pulse_fidelity_left, stat_pulse_fidelity_right
    )

    context["left"]["stat_pulse_fidelity"] = stat_pulse_fidelity_with_improvement
    context["right"]["stat_pulse_fidelity"] = stat_pulse_fidelity_right

    logging.info(
        "Prepared stat_pulse_fidelity and stat_pulse_fidelity_with_improvement"
    )
    return context


# def context_t1_statistics(context, cfg):
#     """Prepare T1 statistics for both experiments."""

#     return context


# def context_t2_statistics(context, cfg):

#     return context


# def context_readout_fidelity_statistics(context, cfg):

#     return context


def context_version_extractor(context, cfg):
    """Prepare calibration data and version information."""

    base_path = Path(cfg.base_dir)

    for label, exp in [
        ("left", Path(cfg.calibration_left) / cfg.run_left),
        ("right", Path(cfg.calibration_right) / cfg.run_right),
    ]:

        with open(base_path / exp /  "version_extractor" / "results.json") as f:
            file = json.load(f)
            context[label]["device"] = file.get("device", "N/A")
            context[label]["calibration_id"] = file.get("commit_hash", "N/A")
            context[label]["calibration_date"] = file.get("commit_date", "Unknown")
            context[label]["calibration_note"] = file.get("commit_message", "N/A")

            context[label]["versions"] = file.get("versions", "N/A")

            context[label]["run_id"] = file.get("run_id", "N/A")
            context[label]["run_date"] = file.get("experiment_date", "Unknown")
            context[label]["run_note"] = file.get("experiment_note", "N/A")
            # import pdb

            # pdb.set_trace()
    logging.info("Prepared calibration data")

    return context


# def context_commit_info(context, cfg):
#     """Prepare commit information for both experiments."""
#     base_path = Path(cfg.base_dir)

#     # Left experiment commit info
#     commit_info = fl.process_commit_info(
#         base_path / cfg.calibration_left / "commit_info.json"
#     )


# def context_commit_info(context, cfg):
#     """Prepare commit information for both experiments."""
#     base_path = Path(cfg.base_dir)

#     # Left experiment commit info
#     commit_info = fl.process_commit_info(
#         base_path / cfg.calibration_left / "commit_info.json"
#     )
#     context["note_left"] = commit_info.get("commit_message", [])
#     context["calibration_date_left"] = commit_info.get(
#         "calibration_date", "Unknown Date"
#     )
#     context["experiment_date_left"] = commit_info.get("experiment_date", "Unknown Date")
#     context["run_left"] = commit_info.get("run_id", "N/A")

#     # Right experiment commit info
#     commit_info_right = fl.process_commit_info(
#         base_path / cfg.calibration_right / "commit_info.json"
#     )
#     context["note_right"] = commit_info_right.get("commit_message", [])
#     context["calibration_date_right"] = commit_info_right.get(
#         "calibration_date", "Unknown Date"
#     )
#     context["experiment_date_right"] = commit_info_right.get(
#         "experiment_date", "Unknown Date"
#     )
#     context["run_right"] = commit_info_right.get("run_id", "N/A")

#     logging.info("Prepared commit information")
#     return context


def context_fidelity_plots_and_table(context, cfg):
    """Prepare fidelity plots and best qubits data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare paths for calibration and results
        calibration_path = base_path / "calibrations"/ calibration / "sinq20" / "calibration.json"
        results_path = base_path / calibration / run / "bell_tomography" / "results.json"

        # Generate fidelity plot
        try:
            context[label]["plot_fidelity"] = pl.plot_fidelity_graph(
                calibration_path,
                results_path,
                f"{calibration}_{run}",
                config.connectivity,
                config.pos,
                output_path=os.path.join("build", "fidelity", calibration, run) + "/",  # Unique output path
            )
        except Exception:
            context[label]["plot_fidelity"] = "placeholder.png"

        # Extract best qubits data
        context[label]["best_qubits"] = fl.extract_best_qubits(results_path)

        # Extract fidelities list for Benchmark Results table
        try:
            context[label]["fidelities_list"] = fl.context_fidelity(
                f"{calibration}/sinq20"
            )
        except Exception as e:
            logging.warning(f"Error preparing fidelities_list for {label}: {e}")
            context[label]["fidelities_list"] = []
    # import pdb

    # pdb.set_trace()

    logging.info("Prepared fidelity plots and best qubits data")
    return context


def context_mermin_plots(context, cfg):
    """Prepare Mermin plots and table data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare paths for results
        results_path = base_path / calibration / run / "mermin" / "results.json"

        try:
            # Extract description only once (from left side)
            if label == "left":
                context["mermin_description"] = fl.extract_description(results_path)

            plot_path, mermin_max = pl.mermin_plot(
                raw_data=results_path,
                expname=f"mermin_{calibration}_{run}",
                output_path="build/",
            )
            context[label]["plot_mermin"] = plot_path
            context[label]["mermin_max"] = mermin_max
            # Extract runtime and qubits used
            context[label][f"mermin_runtime"] = fl.extract_runtime(results_path)
            context[label][f"mermin_qubits"] = fl.extract_qubits_used(results_path)
        except Exception as e:
            logging.warning(f"Using placeholder for Mermin plot due to an error: {e}")
            context[label][f"plot_mermin"] = "placeholder.png"


    context["mermin_plot_is_set"] = True
    logging.info("Added Mermin 5Q plots to context")
    return context


def context_mermin_table(context, cfg):
    """Prepare Mermin table data."""
    from pathlib import Path

    base_path = Path(cfg.base_dir)

    maximum_mermin = fl.get_maximum_mermin(
        base_path / "mermin" / cfg.calibration_left, "results.json"
    )
    maximum_mermin_right = fl.get_maximum_mermin(
        base_path / "mermin" / cfg.calibration_right, "results.json"
    )
    context["mermin_maximum"] = maximum_mermin
    context["mermin_maximum_right"] = maximum_mermin_right
    return context


def context_grover2q_plots(context, cfg):
    """Prepare Grover 2Q plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "grover2q" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["grover2q_description"] = fl.extract_description(results_path)

        # Generate Grover 2Q plot
        try:
            plot_path, max_prob = pl.plot_grover(
                raw_data=results_path,
                expname=f"grover2q_{calibration}_{run}",
                output_path="build/",
            )
            context[label]["plot_grover2q"] = plot_path
            context[label]["grover2q_max_prob"] = max_prob
            # pdb.set_trace()
            # Extract runtime and qubits used
            context[label]["grover2q_runtime"] = fl.extract_runtime(results_path)
            context[label]["grover2q_qubits"] = fl.extract_qubits_used(results_path)
        except Exception:
            context[label]["plot_grover2q"] = "placeholder.png"

    context["grover2q_plot_is_set"] = True
    logging.info("Added Grover 2Q plots to context")
    # import pdb

    # pdb.set_trace()
    return context


def context_grover3q_plots(context, cfg):
    """Prepare Grover 3Q plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "grover3q" / "results.json"

        # Extract description (same for both sides — can store once)
        if label == "left":
            context["grover3q_description"] = fl.extract_description(results_path)

        # Generate Grover 3Q plot
        try:
            plot_path, max_prob = pl.plot_grover(
                raw_data=results_path,
                expname=f"grover3q_{calibration}_{run}",
                output_path="build/",
            )
            context[label]["plot_grover3q"] = plot_path
            context[label]["grover3q_max_prob"] = max_prob

            # Extract runtime and qubits used
            context[label]["grover3q_runtime"] = fl.extract_runtime(results_path)
            context[label]["grover3q_qubits"] = fl.extract_qubits_used(results_path)
        except Exception:
            context[label]["plot_grover3q"] = "placeholder.png"



    context["grover3q_plot_is_set"] = True
    logging.info("Added Grover 3Q plots to context")
    return context


def context_ghz_plots(context, cfg):
    """Prepare GHZ plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "ghz" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["ghz_description"] = fl.extract_description(results_path)

        # Generate GHZ plot
        try:
            plot_path, success_rate = pl.plot_ghz(
                raw_data=results_path,
                experiment_name=calibration,
                output_path=os.path.join(
                        "build",
                        "ghz",
                        calibration,
                        run,
                    ),
            )
            context[label]["plot_ghz"] = plot_path
            context[label]["ghz_success"] = f"{success_rate:.3f}" if success_rate is not None else "N/A"
        except Exception:
            context[label]["plot_ghz"] = "placeholder.png"

        # Extract runtime and qubits used
        context[label]["ghz_runtime"] = fl.extract_runtime(results_path)
        context[label]["ghz_qubits"] = fl.extract_qubits_used(results_path)

    context["ghz_plot_is_set"] = True
    logging.info("Added GHZ plots to context")
    return context


def context_process_tomography_plots(context, cfg):
    """Prepare Process Tomography plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "process_tomography" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["process_tomography_description"] = fl.extract_description(
                results_path
            )

        # Generate Process Tomography plot
        try:
            context[label]["plot_process_tomography"] = pl.plot_process_tomography(
                calid=calibration,
                runid=run,
                output_path=os.path.join("build", "process_tomography", calibration, run),
            )
        except Exception as e:
            logging.error(f"Error generating Process Tomography plot for {label}: {e}")
            context[label]["plot_process_tomography"] = "placeholder.png"

        # Extract runtime
        context[label]["process_tomography_runtime"] = fl.extract_runtime(results_path)

    context["process_tomography_plot_is_set"] = True
    logging.info("Added Process Tomography plots to context")
    return context


def context_tomography_plots(context, cfg):
    """Prepare Tomography plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "tomography" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["tomography_description"] = fl.extract_description(results_path)

        # Generate Tomography plot
        try:
            context[label]["plot_tomography"] = pl.plot_tomography(
                raw_data=results_path,
                output_path=os.path.join("build", "tomography", calibration, run),
            )
        except Exception as e:
            logging.error(f"Error generating Tomography plot for {label}")
            context[label]["plot_tomography"] = "placeholder.png"

    context["tomography_plot_is_set"] = True
    logging.info("Added Tomography plots to context")
    return context


def context_reuploading_classifier_plots(context, cfg):
    """Prepare Reuploading Classifier plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "reuploading_classifier" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["reuploading_classifier_description"] = fl.extract_description(
                results_path
            )

        # import pdb
        # pdb.set_trace()
        # Generate Reuploading Classifier plot
        try:
            context[label]["plot_reuploading_classifier"] = (
                pl.plot_reuploading_classifier(
                    raw_data=results_path,
                    exp_name=calibration,
                    output_path=os.path.join(
                        "build",
                        "reuploading_classifier",
                        calibration,
                    ),
                )
            )
        except Exception:
            context[label]["plot_reuploading_classifier"] = "placeholder.png"

        # Extract runtime and qubits used
        context[label]["reuploading_classifier_runtime"] = fl.extract_runtime(
            results_path
        )
        context[label]["reuploading_classifier_qubits"] = fl.extract_qubits_used(
            results_path
        )

    context["reuploading_classifier_plot_is_set"] = True
    logging.info("Added Reuploading Classifier plots to context")
    return context


def context_qft_plots(context, cfg):
    """Prepare QFT plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "qft" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["qft_description"] = fl.extract_description(results_path)

        # Generate QFT plot
        try:
            context[label]["plot_qft"] = pl.plot_qft(
                raw_data=results_path,
                expname=f"qft_{calibration}_{run}",
                output_path=os.path.join(
                        "build",
                        "qft",
                        calibration,
                    ),
            )
        except Exception:
            context[label]["plot_qft"] = "placeholder.png"

        # Extract runtime and qubits used
        context[label]["qft_runtime"] = fl.extract_runtime(results_path)
        context[label]["qft_qubits"] = fl.extract_qubits_used(results_path)

    context["qft_plot_is_set"] = True
    logging.info("Added QFT plots to context")
    return context


def context_yeast_4q_plots(context, cfg):
    """Prepare Yeast 4Q classification plots and data."""
    context["qml_4Q_yeast_description"] = fl.extract_description(
        os.path.join("data", "qml_4Q_yeast", cfg.calibration_left, "results.json")
    )
    context["qml_4Q_yeast_runtime_left"] = fl.extract_runtime(
        os.path.join("data", "qml_4Q_yeast", cfg.calibration_left, "results.json")
    )
    context["qml_4Q_yeast_runtime_right"] = fl.extract_runtime(
        os.path.join("data", "qml_4Q_yeast", cfg.calibration_right, "results.json")
    )
    context["yeast_classification_4q_plot_is_set"] = True
    context["plot_yeast_4q"] = pl.plot_qml(
        raw_data=os.path.join(
            "data", "qml_4Q_yeast", cfg.calibration_left, "results.json"
        ),
        expname=f"4q_yeast_{cfg.calibration_left}_{run}",
        output_path=os.path.join("build", "yeast", cfg.calibration_left, cfg.run_left),
    )
    context["plot_yeast_4q_right"] = pl.plot_qml(
        raw_data=os.path.join(
            "data", "qml_4Q_yeast", cfg.calibration_right, "results.json"
        ),
        expname=f"4q_yeast_{cfg.calibration_right}_{run}",
        output_path=os.path.join("build", "yeast", cfg.calibration_right, cfg.run_right),
    )
    logging.info("Added Yeast classification 4q plots to context")
    return context


def context_yeast_3q_plots(context, cfg, dataset):
    """Prepare Yeast 3Q classification plots and data."""
    context["yeast_classification_3q_plot_is_set"] = True

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        results_path = os.path.join(
            "data", calibration, run, f"qml_3q_{dataset}", "results.json"
        )

        # Extract accuracy and format to 2 decimal places
        accuracy = fl.get_qml_accuracy(results_path)
        context[label][f"{dataset}_3q_accuracy"] = f"{accuracy:.2f}"

        # Extract runtime/duration
        context[label][f"{dataset}_3q_duration"] = fl.extract_runtime(results_path)

        # Extract qubits used and format as comma-separated string if it's a list
        qubits_used = fl.extract_qubits_used(results_path)
        if isinstance(qubits_used, list):
            context[label][f"{dataset}_3q_qubits"] = ", ".join(map(str, qubits_used))
        else:
            context[label][f"{dataset}_3q_qubits"] = qubits_used

        # Extract description only once (from left side)
        if label == "left":
            context[label][f"{dataset}_3q_description"] = fl.extract_description(results_path)

        # Generate plot
        try:
            context[label][f"plot_{dataset}_3q"] = pl.plot_qml(
                raw_data=results_path,
                expname=f"3q_{dataset}_{calibration}_{run}",
                output_path=os.path.join("build", dataset, calibration, run),
            )
        except Exception as e:
            print(f"Error generating {dataset} 3q plot for {label}: {e}")
            context[label][f"plot_{dataset}_3q"] = "placeholder.png"

    logging.info("Added Yeast classification 3q plots to context")
    # import pdb
    # pdb.set_trace()
    return context


def context_statlog_4q_plots(context, cfg):
    """Prepare StatLog 4Q classification plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / "qml_4Q_statlog" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["statlog_4q_description"] = fl.extract_description(results_path)

        # Generate StatLog 4Q plot
        try:
            context[label]["plot_statlog_4q"] = pl.plot_qml(
                raw_data=results_path,
                expname=f"4q_statlog_{calibration}_{run}",
                output_path=os.path.join(
                    "build",
                    "statlog",
                    calibration,
                    run,
                ),
            )
        except Exception:
            context[label]["plot_statlog_4q"] = "placeholder.png"

        # Extract runtime and qubits used
        context[label]["statlog_4q_runtime"] = fl.extract_runtime(results_path)
        context[label]["statlog_4q_qubits"] = fl.extract_qubits_used(results_path)

    context["statlog_classification_4q_is_set"] = True
    logging.info("Added StatLog classification 4q plots to context")
    return context


def context_statlog_3q_plots(context, cfg):
    """Prepare StatLog 3Q classification plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / "qml_3q_statlog" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["statlog_3q_description"] = fl.extract_description(results_path)

        try:
            context[label]["plot_statlog_3q"] = pl.plot_qml(
                raw_data=results_path,
                expname=f"3q_statlog_{calibration}_{run}",
                output_path=os.path.join(
                    "build",
                    "statlog",
                    calibration,
                    run,
                ),
            )
        except Exception:
            context[label]["plot_statlog_3q"] = "placeholder.png"

        # Extract runtime, accuracy and qubits used
        context[label]["statlog_3q_runtime"] = fl.extract_runtime(results_path)
        context[label]["statlog_3q_accuracy"] = fl.get_qml_accuracy(results_path)
        context[label]["statlog_3q_qubits"] = fl.extract_qubits_used(results_path)

    context["statlog_classification_3q_plot_is_set"] = True
    logging.info("Added StatLog classification 3q plots to context")
    return context


def context_amplitude_encoding_plots(context, cfg):
    """Prepare Amplitude Encoding plots and data."""
    base_path = Path(cfg.base_dir)

    for label, calibration, run in zip(
        ["left", "right"],
        [cfg.calibration_left, cfg.calibration_right],
        [cfg.run_left, cfg.run_right],
    ):
        # Prepare path for results
        results_path = base_path / calibration / run / "amplitude_encoding" / "results.json"

        # Extract description only once (from left side)
        if label == "left":
            context["amplitude_encoding_description"] = fl.extract_description(
                results_path
            )

        # Generate Amplitude Encoding plot
        try:
            context[label]["plot_amplitude_encoding"] = pl.plot_amplitude_encoding(
                raw_data=results_path,
                expname=f"amplitude_encoding_{calibration}_{run}",
                output_path=os.path.join(
                        "build",
                        "amplitude_encoding",
                        calibration,
                        run,
                    ),
            )
        except Exception:
            context[label]["plot_amplitude_encoding"] = "placeholder.png"

        # Extract runtime and qubits used
        context[label]["amplitude_encoding_runtime"] = fl.extract_runtime(results_path)
        context[label]["amplitude_encoding_qubits"] = fl.extract_qubits_used(
            results_path
        )

    context["amplitude_encoding_plot_is_set"] = True
    logging.info("Added Amplitude Encoding plots to context")

    return context
