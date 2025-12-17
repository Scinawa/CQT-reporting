#!/bin/bash

# CQT Reporting Periodic Script
# Runs weekly to generate and publish reports

set -e

PROJECT_DIR="/opt/cqt-reporting"
cd "$PROJECT_DIR"

# Add uv to PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

echo "$(date): Starting weekly report generation"

# Pull latest changes
echo "$(date): Pulling latest changes from repository"
git pull origin main

# Activate uv virtual environment
echo "$(date): Activating virtual environment"
source .venv/bin/activate

# Download latest data
echo "$(date): Downloading latest data"
python3 download.py --last-two

# Compile PDF
echo "$(date): Compiling PDF report"
make pdf

# Check if PDF was generated successfully
if [ -f "report/latest_report.pdf" ]; then
    echo "$(date): PDF generated successfully"
    
    # Add and commit the new report
    git add report/latest_report.pdf
    git commit -m "Automated weekly report update - $(date +%Y-%m-%d)"
    
    # Push to GitHub
    echo "$(date): Pushing to GitHub"
    git push origin main
    
    echo "$(date): Weekly report generation completed successfully"
else
    echo "$(date): ERROR - PDF generation failed"
    exit 1
fi
