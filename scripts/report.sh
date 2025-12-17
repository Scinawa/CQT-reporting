#!/usr/bin/env bash
set -e

##############################
# Default Configuration
##############################

calibration_right="${calibration_right:-1e1f7e1d1af58009eda1986bb3689e6b9b2356b6}"
RUNID_RIGHT="${RUNID_RIGHT:-20251123023814}"

calibration_left="${calibration_left:-3826882f81128980b5e49b0e1bec76e24e40e158}"
RUNID_LEFT="${RUNID_LEFT:-20251201101512}"

PYTHON=".venv/bin/python"   # ensures uv environment is used
LATEX="pdflatex"
DATESTAMP=$(date +%d%m%Y_%H)

##############################
# Helper: ensure venv exists
##############################

ensure_venv() {
    if [ ! -f ".venv/bin/python" ]; then
        echo "No uv environment detected. Running uv sync..."
        uv sync
    fi
}

##############################
# Download commands
##############################

download_latest_two() {
    mkdir -p data
    echo "Downloading latest two experiments..."
    $PYTHON download.py --latest-two
}

download_data() {
    mkdir -p data
    echo "Downloading data for experiment $calibration_left"
    $PYTHON download.py --hash-id "$calibration_left" --run-id "$RUNID_LEFT"

    echo "Downloading data for experiment $calibration_right"
    $PYTHON download.py --hash-id "$calibration_right" --run-id "$RUNID_RIGHT"
}

##############################
# Build report
##############################

clean() {
    echo "Cleaning build directory..."
    rm -rf build/*
}

build() {
    ensure_venv
    clean
    mkdir -p build
    cp src/templates/placeholder.png build/placeholder.png

    echo "Building LaTeX report..."
    $PYTHON src/main.py \
        --calibration-left "$calibration_left" \
        --calibration-right "$calibration_right" \
        --run-left "$RUNID_LEFT" \
        --run-right "$RUNID_RIGHT" \
        # --no-tomography-plot
}

##############################
# Compile LaTeX to PDF
##############################

pdf_only() {
    echo "Compiling LaTeX to PDF..."
    mkdir -p logs

    $LATEX -output-directory=build report.tex > logs/pdflatex.log

    cp build/report.pdf .
    cp build/report.pdf "reports/report_${calibration_left:0:10}_vs_${calibration_right:0:10}_${DATESTAMP}.pdf"
    cp build/report.pdf reports/latest_report.pdf

    echo "PDF generated."
}

pdf() {
    build
    pdf_only
}

##############################
# High-level PDF helpers
##############################

best_latest_pdf() {
    echo "Downloading BEST result (right side)..."
    mkdir -p data
    # download.py 'best' prints: <hashID> <runID> on stdout
    read calibration_right RUNID_RIGHT < <("$PYTHON" download.py best)
    echo "  calibration_right=$calibration_right"
    echo "  RUNID_RIGHT=$RUNID_RIGHT"

    echo "Downloading LATEST result (left side)..."
    # download.py 'latest' prints: <hashID> <runID> on stdout
    read calibration_left RUNID_LEFT < <("$PYTHON" download.py latest)
    echo "  calibration_left=$calibration_left"
    echo "  RUNID_LEFT=$RUNID_LEFT"

    # Now build and compile the report using these values
    pdf
}

specific_pdf() {
    if [ "$#" -ne 5 ]; then
        echo "Usage: $0 specific-pdf CALIB_LEFT RUN_LEFT CALIB_RIGHT RUN_RIGHT" >&2
        exit 1
    fi

    # Positional arguments:
    #   $2 = CALIB_LEFT
    #   $3 = RUN_LEFT
    #   $4 = CALIB_RIGHT
    #   $5 = RUN_RIGHT
    calibration_left="$2"
    RUNID_LEFT="$3"
    calibration_right="$4"
    RUNID_RIGHT="$5"

    mkdir -p data

    echo "Downloading specific LEFT result: hashID=$calibration_left runID=$RUNID_LEFT"
    "$PYTHON" download.py specific "$calibration_left" "$RUNID_LEFT" >/dev/null

    echo "Downloading specific RIGHT result: hashID=$calibration_right runID=$RUNID_RIGHT"
    "$PYTHON" download.py specific "$calibration_right" "$RUNID_RIGHT" >/dev/null

    # Now build and compile the report using these explicit values
    pdf
}




##############################
# Command-line interface
##############################

case "$1" in
    download-latest-two) download_latest_two ;;
    download-data)       download_data ;;
    clean)               clean ;;
    build)               build ;;
    pdf-only)            pdf_only ;;
    pdf)                 pdf ;;
    best-latest-pdf)     best_latest_pdf "$@" ;;
    specific-pdf)        specific_pdf "$@" ;;
    *)
        echo "Usage: $0 {download-latest-two|download-data|clean|build|pdf-only|pdf|best-latest-pdf|specific-pdf}"
        exit 1
        ;;
esac
