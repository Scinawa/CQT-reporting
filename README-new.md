# CQT Benchmarking Report Generator

Generates side-by-side PDF comparison reports for two quantum computing runs. Downloads calibration and experiment data from a remote server, extracts metrics, produces plots, renders LaTeX, and outputs a PDF.

Currently targets the **sinq20** platform but calibration bundles may include data for other platforms (e.g. sinq-5).

## Pipeline

```
Remote API (54.169.91.191)
  → download.py fetches ZIP archives
    → data/<calibration-hash>/<run-id>/<experiment>/results.json
      → src/main.py orchestrates report generation
        → fillers.py extracts metrics from JSON
        → plots.py generates matplotlib figures
        → prepare_context.py assembles left-vs-right context dict
          → Jinja2 renders report_template.j2 → report.tex
            → pdflatex compiles → report.pdf
```

## Modules

| File | Role |
|------|------|
| `download.py` | CLI to fetch data from remote API. Modes: `best`, `latest`, `specific`. Outputs `<hashID> <runID>` to stdout for scripting. |
| `clientdb/client.py` | API client library. Wraps `/calibrations/*`, `/results/*`, `/bestruns/*` endpoints. Handles ZIP upload/download, base64 encoding, config persistence (`~/.qibo_client.json`). |
| `server.py` (root) | Flask web UI on port 5000. Pick two runs from dropdowns and generate a comparison PDF. |
| `src/main.py` | Orchestrator. Parses CLI args (`--calibration-left/right`, `--run-left/right`, `--no-*-plot` toggles), calls context builders, renders Jinja2 template to `report.tex`. |
| `src/prepare_context.py` | Builds the full template context dict. One `context_*()` function per experiment type, each populating left/right data. Calls into `fillers.py` and `plots.py`. Computes improvement percentages via `add_stat_changes()`. |
| `src/fillers.py` | Extracts metrics from calibration and result JSONs: T1/T2 coherence stats, gate fidelity, readout fidelity, runtime, qubits used, QML accuracy, Mermin values, best-qubit selections. |
| `src/plots.py` | Matplotlib/NetworkX visualizations: fidelity heatmap on qubit grid, Mermin bars, Grover probabilities, GHZ states, process tomography, QFT, QML confusion matrices, reuploading classifier curves, amplitude encoding. |
| `src/config.py` | Hardware topology: qubit connectivity edges and grid positions for graph layout. Currently defines sinq20 (20 qubits, 30 edges). |
| `src/templates/report_template.j2` | Jinja2 LaTeX template. Renders side-by-side comparison with stats tables, plots, and experiment metadata. Uses custom `tau-class/` document class. |
| `src/server.py` | Async aiohttp server with JWT auth. Endpoints: `/generate_report`, `/download_report`. Uses SQLite `credentials.db`. |
| `src/bootstrap_server.py` | Initializes SQLite user database for the aiohttp server. |
| `src/client.py` | JWT client for the aiohttp server. Generates tokens, triggers remote report generation, downloads PDFs. Config via `.secrets.toml` (Dynaconf). |
| `experiment_list.ini` | Toggles which experiments are enabled, grouped by qubit count. |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/report.sh` | Main automation. Commands: `download-data`, `build`, `pdf`, `best-latest-pdf`, `specific-pdf`. Handles venv setup, data download, LaTeX generation, PDF compilation, and archival to `reports/`. |
| `scripts/periodic.sh` | Cron-job script. Git pulls, downloads latest data, generates PDF, commits and pushes. Runs on `/opt/cqt-reporting`. |
| `scripts/sync-nqch.sh` | Rsyncs experiment data from NQCH machine to reporting server with automatic backups. |

## Supported Experiments

| Qubits | Experiments |
|--------|------------|
| calibration | `bell_tomography`, `version_extractor` |
| 1 | `reuploading_classifier`, `coherence`, `readout`, `standard_rb` |
| 2 | `grover2q`, `process_tomography` |
| 3 | `ghz`, `mermin`, `grover3q`, `qft`, `amplitude_encoding`, `qml_3Q_yeast`, `qml_3Q_statlog` |
| 4 | `qml_4Q_yeast`, `qml_4Q_statlog` |

## Usage

```bash
# Install dependencies (requires Python >=3.12 and uv)
uv sync

# Generate PDF comparing best vs latest run (download + build + compile)
./scripts/report.sh best-latest-pdf

# Generate PDF for specific runs (download + build + compile)
./scripts/report.sh specific-pdf <calib_left> <run_left> <calib_right> <run_right>

# Or step by step:
./scripts/report.sh download-data   # download configured runs
./scripts/report.sh build            # generate report.tex
./scripts/report.sh pdf-only         # compile to PDF
./scripts/report.sh pdf              # build + compile in one step

# Web UI (ad-hoc comparisons)
python server.py   # http://localhost:5000
```

## Repository Structure

```
CQT-reporting/
├── server.py                        # Flask web UI (port 5000)
├── download.py                      # CLI data downloader (best/latest/specific)
├── experiment_list.ini              # Experiment toggles by qubit count
├── pyproject.toml                   # Dependencies and project metadata
│
├── src/
│   ├── main.py                      # Orchestrator: args → context → LaTeX
│   ├── prepare_context.py           # Assembles left-vs-right template context
│   ├── fillers.py                   # Metric extraction from JSON results
│   ├── plots.py                     # Matplotlib/NetworkX visualizations
│   ├── config.py                    # Qubit connectivity and grid positions
│   ├── utils.py                     # LaTeX escaping, data loading helpers
│   ├── server.py                    # Async aiohttp server (JWT auth)
│   ├── bootstrap_server.py          # SQLite user DB setup
│   ├── client.py                    # JWT client for aiohttp server
│   └── templates/
│       ├── report_template.j2       # Jinja2 → LaTeX template
│       ├── placeholder.png          # Fallback when plots fail
│       └── tau-class/               # Custom LaTeX document class
│
├── clientdb/
│   └── client.py                    # Remote API client library
│
├── scripts/
│   ├── report.sh                    # Main automation (build, pdf, download)
│   ├── periodic.sh                  # Cron-job: pull → download → pdf → push
│   └── sync-nqch.sh                 # Rsync data from NQCH machine
│
├── data/                            # Downloaded experiment data
│   ├── calibrations/<hash>/sinq20/  #   calibration.json, platform config
│   └── <hash>/<run-id>/<experiment>/#   results.json per experiment
│
├── reports/                         # Archived PDFs (timestamped + latest_report.pdf)
└── logs/                            # download.log, pdflatex.log, runscripts.log
```

## Key Dependencies

`jinja2`, `matplotlib`, `networkx`, `numpy`, `scikit-learn`, `requests`, `aiohttp`, `pyjwt`, `dynaconf`, `tabulate`, `jsonschema`

Build requires: `pdflatex`, `uv`
