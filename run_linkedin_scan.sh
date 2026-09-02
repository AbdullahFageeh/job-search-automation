#!/bin/bash
# Local Automation Script — Runs LinkedIn scraping (requires Comet browser + your Mac)
# Use this when your Mac is on and you want to scan LinkedIn

cd "$(dirname "$0")"

echo "=========================================="
echo "🔗 LOCAL LINKEDIN SCAN (Comet Browser)"
echo "=========================================="
echo ""
echo "This will open Comet browser and scan LinkedIn for entry-level jobs."
echo "If LinkedIn is already logged in in Comet, it will work automatically!"
echo ""
read -p "Press Enter to start scanning LinkedIn... "

# Scan LinkedIn entry-level jobs
python3 entry_level_jobs.py scan

echo ""
echo "=========================================="
echo "✅ LinkedIn scan complete!"
echo "=========================================="
echo ""
echo "To run full pipeline (all boards + LinkedIn):"
echo "  ./run_full_automation.sh 10"
echo ""