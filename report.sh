#!/usr/bin/env bash
set -e

PYTHON=".venv/bin/python"   # ensures uv environment is used
LATEX="pdflatex"
DATESTAMP=$(date +%d%m%Y_%H)

# Parse --show-errors from any position in the argument list
SHOW_ERRORS=""
for arg in "$@"; do
    case "$arg" in
        --show-errors|--show-errors=true|--show-errors=True)
            SHOW_ERRORS="--show-errors"
            ;;
    esac
done

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

latest_2nd_latest_pdf() {
    mkdir -p data
    echo "Downloading latest two experiments..."

    # download.py 'latest-two' prints two lines to stdout: newest run first
    # Capture both lines; assign newest to left, second newest to right
    latest_two_output=$("$PYTHON" download.py latest-two)

    if [ -z "$latest_two_output" ]; then
        echo "Error: latest-two returned no results" >&2
        exit 1
    fi

    read calibration_left RUNID_LEFT <<< "$(echo "$latest_two_output" | head -1)"
    read calibration_right RUNID_RIGHT <<< "$(echo "$latest_two_output" | tail -1)"

    echo "  calibration_left=$calibration_left  RUNID_LEFT=$RUNID_LEFT"
    echo "  calibration_right=$calibration_right  RUNID_RIGHT=$RUNID_RIGHT"

    # Build the report: left=newest run, right=second newest run
    pdf
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
        $SHOW_ERRORS
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

latest_best_pdf() {
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

specific_left_best_right_pdf() {
    if [ "$#" -ne 3 ]; then
        echo "Usage: $0 specific_left-best_right-pdf CALIB_LEFT RUN_LEFT" >&2
        exit 1
    fi

    # Positional arguments:
    #   $2 = CALIB_LEFT
    #   $3 = RUN_LEFT
    calibration_left="$2"
    RUNID_LEFT="$3"

    mkdir -p data

    echo "Downloading specific LEFT result: hashID=$calibration_left runID=$RUNID_LEFT"
    "$PYTHON" download.py specific "$calibration_left" "$RUNID_LEFT" >/dev/null

    echo "Downloading BEST result (right side)..."
    read calibration_right RUNID_RIGHT < <("$PYTHON" download.py best)
    echo "  calibration_right=$calibration_right"
    echo "  RUNID_RIGHT=$RUNID_RIGHT"

    # Now build and compile the report using these values
    pdf
}

specific_left_specific_right_pdf() {
    if [ "$#" -ne 5 ]; then
        echo "Usage: $0 specific_left-specific_right-pdf CALIB_LEFT RUN_LEFT CALIB_RIGHT RUN_RIGHT" >&2
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
    latest-2nd_latest-pdf)          latest_2nd_latest_pdf ;;
    latest-best-pdf)                latest_best_pdf "$@" ;;
    specific_left-specific_right-pdf) specific_left_specific_right_pdf "$@" ;;
    specific_left-best_right-pdf)   specific_left_best_right_pdf "$@" ;;
    clean)               clean ;;
    *)
        echo "Usage: $0 {latest-2nd_latest-pdf|latest-best-pdf|specific_left-specific_right-pdf|specific_left-best_right-pdf|clean}"
        exit 1
        ;;
esac
