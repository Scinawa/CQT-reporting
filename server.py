from flask import Flask, render_template_string, request, send_file
import os
import subprocess
import configparser
import re

app = Flask(__name__)

BASE_DIR = "data"
PDF_OUTPUT = "report.pdf"  # your script should overwrite/produce this


def load_experiment_list(config_file="experiment_list.ini", logger=None):
    """
    Load experiment list from an INI configuration file.

    Args:
        config_file (str): Path to the experiment list INI configuration file

    Returns:
        dict: Dictionary with sections as keys and lists of experiments as values
    """
    experiments = {}
    try:
        config = configparser.ConfigParser()
        config.read(config_file)

        for section in config.sections():
            experiments[section] = []
            for key, value in config[section].items():
                # Only include experiments that are enabled (not commented out)
                if not key.startswith("#") and value.lower() in [
                    "enabled",
                    "true",
                    "1",
                ]:
                    experiments[section].append(key)

    except Exception as e:
        logger.error(f"Error reading experiment list from '{config_file}': {e}")
        return {}
    return experiments


def is_sha256(s):
    return bool(re.fullmatch(r"[a-fA-F0-9]{40}", s))

def filter_first_level(strings):
    """
    Splits a list of strings into two lists:
    - calibration_ids: strings that are valid SHA256 hashes
    - experiment_lists: strings that are not SHA256 hashes

    Args:
        strings (list): List of strings to filter

    Returns:
        tuple: (calibration_ids, experiment_lists)
    """
    calibration_ids = []
    experiment_lists = []
    for s_tring in strings:
        print(s_tring)
        if is_sha256(s_tring):
            calibration_ids.append(s_tring)
        else:
            experiment_lists.append(s_tring)
    return calibration_ids, experiment_lists

def get_comparable_runs():
    """
    Return all [calibration, run-id] pairs found under data/<calibration-id>/<run-id>/.
    Returns a list of lists: [ [calibration_id, run_id], ... ]
    """
    result = []
    base_dir = os.path.join(BASE_DIR)
    if not os.path.exists(base_dir):
        return result

    for entry in os.listdir(base_dir):
        if entry == "calibrations":
            continue
        entry_path = os.path.join(base_dir, entry)
        # Only consider calibration-id folders (skip 'calibrations', etc.)
        if not os.path.isdir(entry_path):
            continue
        # Optionally, check if entry is a valid calibration-id (SHA1 or SHA256)
        # if not is_sha256(entry):
        #     continue
        for run_id in os.listdir(entry_path):
            run_path = os.path.join(entry_path, run_id)
            if os.path.isdir(run_path):
                result.append([entry, run_id])
    return result



HTML_FORM = """
<!doctype html>
<html>
    <body>
        <h2>Select two run IDs to compare</h2>
        <form action="/generate" method="post">
            <label>Run ID 1:</label>
            <select name="dir1">
                {% for pair in run_ids %}
                    <option value="{{pair[0]}}/{{pair[1]}}">{{pair[0]}}/{{pair[1]}}</option>
                {% endfor %}
            </select><br><br>

            <label>Run ID 2:</label>
            <select name="dir2">
                {% for pair in run_ids %}
                    <option value="{{pair[0]}}/{{pair[1]}}">{{pair[0]}}/{{pair[1]}}</option>
                {% endfor %}
            </select><br><br>

            <input type="submit" value="Generate PDF">
        </form>
    </body>
</html>
"""

@app.route("/")
def index():
    run_ids = get_comparable_runs()
    return render_template_string(HTML_FORM, run_ids=run_ids)

@app.route("/generate", methods=["POST"])
def generate():
    d1 = request.form["dir1"]
    d2 = request.form["dir2"]

    # Split calibration-id and run-id
    cal1, run1 = d1.split("/", 1)
    cal2, run2 = d2.split("/", 1)
    # You can now use cal1, run1, cal2, run2 as needed

    # Call your PDF generation script
    print("generating pdf with ", cal1, cal2, run1, run2)
    subprocess.run(["python3", "src/main.py", "--calibration-left", cal1,
		"--calibration-right", cal2,
		"--run-left", run1,
		"--run-right", run2,
        ], check=True)

    return send_file(PDF_OUTPUT, as_attachment=True, download_name="comparison.pdf")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)