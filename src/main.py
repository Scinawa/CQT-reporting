import argparse
from multiprocessing import context
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import logging
import os
import json
import numpy as np
import fillers as fl
import sys
import plots as pl
import config
import pdb

from prepare_context import (
    context_fidelity_plots_and_table,
    context_mermin_plots,
    context_mermin_table,
    context_grover2q_plots,
    context_grover3q_plots,
    context_ghz_plots,
    context_process_tomography_plots,
    context_tomography_plots,
    context_reuploading_classifier_plots,
    context_qft_plots,
    context_yeast_4q_plots,
    context_yeast_3q_plots,
    context_statlog_4q_plots,
    context_statlog_3q_plots,
    context_amplitude_encoding_plots,
    add_stat_changes,
    # context_fidelity_statistics,
    # context_pulse_fidelity_statistics,
    # context_t1_statistics,
    # context_t2_statistics,
    # context_readout_fidelity_statistics,
    # context_calibration_data,
    # context_commit_info,
    context_version_extractor,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def setup_argument_parser():
    """Set up the command line argument parser."""
    parser = argparse.ArgumentParser(description="Generate a quantum benchmark report.")
    parser.add_argument(
        "--base_dir",
        type=str,
        default="data/",
        help="Base directory for data and output.",
    )

    parser.add_argument(
        "--calibration-right",
        type=str,
        default="9848c933bfcafbb8f81c940f504b893a2fa6ac23",
        help="Directory containing the experiment data.",
    )
    parser.add_argument(
        "--calibration-left",
        type=str,
        default="numpy",
        help="Directory containing the experiment data.",
    )
    parser.add_argument(
        "--run-right",
        type=str,
        default="",
        help="Run id for the right experiment.",
    )
    parser.add_argument(
        "--run-left",
        type=str,
        default="",
        help="Run id for the left experiment.",
    )

    # Plot toggles (default: True). Use --no-<flag> to disable.
    parser.add_argument(
        "--no-t1-plot", dest="t1_plot", default=False, action="store_false"
    )
    parser.add_argument("--no-mermin-plot", dest="mermin_plot", action="store_false")
    parser.add_argument(
        "--no-reuploading-plot", dest="reuploading_plot", action="store_false"
    )
    parser.add_argument(
        "--no-grover2q-plot", dest="grover2q_plot", action="store_false"
    )
    parser.add_argument(
        "--no-grover3q-plot", dest="grover3q_plot", action="store_false"
    )

    parser.add_argument("--no-ghz-plot", dest="ghz_plot", action="store_false")
    parser.add_argument(
        "--no-process-tomography-plot",
        dest="process_tomography_plot",
        action="store_false",
    )
    parser.add_argument(
        "--no-qft-plot",
        dest="qft_plot",
        action="store_false",
    )
    parser.add_argument(
        "--no-tomography-plot", dest="tomography_plot", action="store_false"
    )
    parser.add_argument(
        "--no-reuploading-classifier-plot",
        dest="reuploading_classifier_plot",
        action="store_false",
    )
    parser.add_argument(
        "--no-yeast-plot-4q", dest="yeast_plot_4q", action="store_false"
    )
    parser.add_argument(
        "--no-yeast-plot-3q", dest="yeast_plot_3q", action="store_false"
    )
    parser.add_argument(
        "--no-statlog-plot-4q", dest="statlog_plot_4q", action="store_false"
    )
    parser.add_argument(
        "--no-statlog-plot-3q", dest="statlog_plot_3q", action="store_false"
    )
    parser.add_argument(
        "--no-amplitude-encoding-plot",
        dest="amplitude_encoding_plot",
        action="store_false",
    )
    return parser


def prepare_template_context(cfg):
    """
    Prepare a complete template context for the benchmarking report.
    """
    logging.info("Preparing context for full benchmarking report.")

    context = {"left": {}, "right": {}}

    # create left and right box of version data
    try:
        context = context_version_extractor(context, cfg)
    except Exception as e:
        print(e)
        logging.error(f"Error preparing metadata: {e}")
        # Fallback metadata for both sides
        default_meta = {
            "experiment_name": "Unknown",
            "platform": "Unknown",
            "start_time": "Unknown",
            "end_time": "Unknown",
        }
        context.setdefault("left", {}).update(default_meta)
        context.setdefault("right", {}).update(default_meta)

    ##### T1 statistics
    try:
        stat_t1 = fl.get_stat_t12("calibrations/"+cfg.calibration_left + "/sinq20", "t1")
        stat_t1_right = fl.get_stat_t12("calibrations/"+cfg.calibration_right + "/sinq20", "t1")
        stat_t1_with_improvement = add_stat_changes(stat_t1, stat_t1_right)

        context["left"]["stat_t1"] = stat_t1_with_improvement
        context["right"]["stat_t1"] = stat_t1_right


        logging.info("Prepared stat_t1 and stat_t1_with_improvement")

    except Exception as e:
        logging.error(f"Error preparing statistics 1 table: {e}")


    ##### T2 statistics
    try:    
        """Prepare T2 statistics for both experiments."""
        stat_t2 = fl.get_stat_t12("calibrations/" + cfg.calibration_left + "/sinq20", "t2")
        stat_t2_right = fl.get_stat_t12("calibrations/" + cfg.calibration_right + "/sinq20", "t2")
        stat_t2_with_improvement = add_stat_changes(stat_t2, stat_t2_right)

        context["left"]["stat_t2"] = stat_t2_with_improvement
        context["right"]["stat_t2"] = stat_t2_right

        logging.info("Prepared stat_t2 and stat_t2_with_improvement")
    except Exception as e:
        logging.error(f"Error preparing statistics 2 table: {e}")

    # import pdb
    # pdb.set_trace()

    ##### FIDELITY 
    try:
        """Prepare fidelity statistics for both experiments."""
        stat_fidelity = fl.get_stat_fidelity(
            os.path.join("data", "calibrations", cfg.calibration_left, "sinq20", "calibration.json"),
            cfg.calibration_left,
        )
        stat_fidelity_right = fl.get_stat_fidelity(
            os.path.join("data", "calibrations", cfg.calibration_right, "sinq20", "calibration.json"),
            cfg.calibration_right,
        )
        stat_fidelity_with_improvement = add_stat_changes(
            stat_fidelity, stat_fidelity_right
        )

        context["left"]["stat_fidelity"] = stat_fidelity_with_improvement
        context["right"]["stat_fidelity"] = stat_fidelity_right

        logging.info("Prepared stat_fidelity and stat_fidelity_with_improvement")
    except Exception as e:
        logging.error(f"Error preparing statistics 1' table: {e}")

    ##### READOUT FIDELITY
    try:
        """Prepare readout fidelity statistics for both experiments."""
        stat_readout_fidelity = fl.get_readout_fidelity(
            os.path.join("data", "calibrations", cfg.calibration_left, "sinq20", "calibration.json"),
            cfg.calibration_left,
        )
        stat_readout_fidelity_right = fl.get_readout_fidelity(
            os.path.join("data", "calibrations", cfg.calibration_right, "sinq20", "calibration.json"),
            cfg.calibration_right,
        )

        context["left"]["stat_readout_fidelity"] = stat_readout_fidelity
        context["right"]["stat_readout_fidelity"] = stat_readout_fidelity_right

        logging.info("Prepared readout fidelity statistics")
    except Exception as e:
        logging.error(f"Error preparing statistics 2' table: {e}")
        # context = context_mermin_table(context, cfg)
        # context = context_pulse_fidelity_statistics(context, cfg)



    # FIDELITY PLOT MAIN PAGE
    try:
        context = context_fidelity_plots_and_table(context, cfg)
    except Exception as e:
        logging.error(f"Error preparing fidelity plots: {e}")
        context["plot_exp"] = "placeholder.png"
        context["plot_right"] = "placeholder.png"
        context["best_qubits_left"] = {
            k: {"qubits": "N/A", "fidelity": "N/A"} for k in ["2", "3", "4", "5"]
        }
        context["best_qubits_right"] = {
            k: {"qubits": "N/A", "fidelity": "N/A"} for k in ["2", "3", "4", "5"]
        }

    # MERMIN
    if cfg.mermin_plot:
        try:
            context = context_mermin_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing Mermin plots: {e}")
            context["mermin_plot_is_set"] = None
    else:
        context["mermin_plot_is_set"] = None

    # GROVER 2Q PLOTS
    if cfg.grover2q_plot:
        try:
            context = context_grover2q_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing Grover 2Q plots: {e}")
            context["grover2q_plot_is_set"] = None
    else:
        logging.info("Grover 2Q plot is not set, skipping...")
        context["grover2q_plot_is_set"] = None

    # GROVER 3Q PLOTS
    if cfg.grover3q_plot:
        try:
            context = context_grover3q_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing Grover 3Q plots: {e}")
            context["grover3q_plot_is_set"] = None
    else:
        logging.info("Grover 3Q plot is not set, skipping...")
        context["grover3q_plot_is_set"] = None

    # GHZ PLOTS
    if cfg.ghz_plot:
        try:
            context = context_ghz_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing GHZ plots: {e}")
            context["ghz_plot_is_set"] = None
    else:
        logging.info("GHZ plot is not set, skipping...")
        context["ghz_plot_is_set"] = None

    # # tomography
    # if cfg.tomography_plot:
    #     try:
    #         context = context_tomography_plots(context, cfg)
    #     except Exception as e:
    #         logging.error(f"Error preparing Tomography plots: {e}")
    #         context["tomography_plot_is_set"] = None
    # else:
    #     logging.info("Tomography plot is not set, skipping...")
    #     context["tomography_plot_is_set"] = None

    # PROCESS TOMOGRAPHY PLOTS
    if cfg.process_tomography_plot:
        try:
            context = context_process_tomography_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing Process Tomography plots: {e}")
            context["process_tomography_plot_is_set"] = None
    else:
        logging.info("Process Tomography plot is not set, skipping...")
        context["process_tomography_plot_is_set"] = None

    # import pdb
    # pdb.set_trace()

    # REUPLOADING CLASSIFIER PLOTS
    if cfg.reuploading_classifier_plot:
        try:
            context = context_reuploading_classifier_plots(context, cfg)
        except Exception as e:
            print(e)
            logging.error(f"Error preparing Reuploading Classifier plots: {e}")
            context["reuploading_classifier_plot_is_set"] = None
    else:
        logging.info("Reuploading Classifier plot is not set, skipping...")
        context["reuploading_classifier_plot_is_set"] = None

    # QFT PLOTS
    if cfg.qft_plot:
        try:
            context = context_qft_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing QFT plots: {e}")
            context["qft_plot_is_set"] = None
    else:
        logging.info("QFT plot is not set, skipping...")
        context["qft_plot_is_set"] = None

    # # YEAST CLASSIFICATION 4Q PLOTS
    # if cfg.yeast_plot_4q:
    #     try:
    #         context = context_yeast_4q_plots(context, cfg)
    #     except Exception as e:
    #         logging.error(f"Error preparing Yeast 4Q plots: {e}")
    #         context["yeast_classification_4q_plot_is_set"] = None
    # else:
    #     logging.info("Yeast 4Q plot is not set, skipping...")
    #     context["yeast_classification_4q_plot_is_set"] = None

    # # STATLOG CLASSIFICATION 4Q PLOTS
    # if cfg.statlog_plot_4q:
    #     try:
    #         context = context_statlog_4q_plots(context, cfg)
    #     except Exception as e:
    #         logging.error(f"Error preparing StatLog 4Q plots: {e}")
    #         context["statlog_classification_4q_plot_is_set"] = None
    # else:
    #     logging.info("StatLog 4Q plot is not set, skipping...")
    #     context["statlog_classification_4q_plot_is_set"] = None

    # STATLOG CLASSIFICATION 3Q PLOTS
    if cfg.statlog_plot_3q:
        try:
            context = context_yeast_3q_plots(context, cfg, "statlog")
        except Exception as e:
            logging.error(f"Error preparing StatLog 3Q plots: {e}")
            context["statlog_classification_3q_plot_is_set"] = None
    else:
        logging.info("StatLog 3Q plot is not set, skipping...")
        context["statlog_classification_3q_plot_is_set"] = None

    # YEAST CLASSIFICATION 3Q PLOTS
    if cfg.yeast_plot_3q:
        try:
            context = context_yeast_3q_plots(context, cfg, "yeast")
        except Exception as e:
            logging.error(f"Error preparing Yeast 3Q plots: {e}")
            context["yeast_classification_3q_plot_is_set"] = None
    else:
        logging.info("Yeast 3Q plot is not set, skipping...")
        context["yeast_classification_3q_plot_is_set"] = None



    # AMPLITUDE ENCODING PLOTS
    if cfg.amplitude_encoding_plot:
        try:
            context = context_amplitude_encoding_plots(context, cfg)
        except Exception as e:
            logging.error(f"Error preparing Amplitude Encoding plots: {e}")
            context["amplitude_encoding_plot_is_set"] = None
    else:
        logging.info("Amplitude Encoding plot is not set, skipping...")
        context["amplitude_encoding_plot_is_set"] = None

    return context


def render_and_save_report(context, args):
    """
    Render the LaTeX template and save the generated report.

    Args:
        context: Template context dictionary.
        args: Parsed command line arguments.

    Returns:
        Path to the generated LaTeX file.
    """
    logging.info("Rendering LaTeX template...")
    # Setup Jinja2 environment and load template
    template_dir = Path("src/templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report_template.j2")

    # Render template with context
    rendered_content = template.render(context)

    # Ensure build directory exists
    build_dir = Path(".")
    build_dir.mkdir(exist_ok=True)

    # Write rendered LaTeX file in the build directory using os.path.join
    output_file = os.path.join(build_dir, "report.tex")
    with open(output_file, "w") as f:
        f.write(rendered_content)
        return output_file

    raise RuntimeError("Failed to render the report template.")


def main():
    """
    Main function that orchestrates the quantum benchmark report generation process.
    """
    logging.info("Starting report generation process...")

    # Step 1: Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()

    # Step 2: Prepare template context with all required data
    context = prepare_template_context(args)

    # Step 3: Render and save the LaTeX report
    output_file = render_and_save_report(context, args)
    logging.info(f"Report generated at: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
