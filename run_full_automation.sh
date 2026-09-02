#!/bin/bash
# Full Automation Run Script
# Usage: ./run_full_automation.sh [num_jobs_to_apply]

cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 FULL JOB SEARCH AUTOMATION PIPELINE"
echo "=========================================="

NUM_JOBS=${1:-10}

# 1. Scan for entry-level jobs
echo -e "\n📋 Step 1: Scanning for entry-level jobs..."
python3 entry_level_jobs.py scan

# 2. Scan other boards
echo -e "\n📋 Step 2: Scanning other job boards..."
python3 other_boards_monitor.py once

# 3. Check for new jobs with alerts
echo -e "\n📋 Step 3: Checking for new jobs (alerts)..."
python3 job_alerts.py --once

# 4. Auto-apply to jobs (uses Comet browser)
echo -e "\n📋 Step 4: Auto-applying to $NUM_JOBS jobs..."
python3 auto_apply.py "$NUM_JOBS"

# 5. Generate daily digest
echo -e "\n📋 Step 5: Generating daily digest..."
python3 daily_digest.py

# 6. Show application tracker
echo -e "\n📋 Step 6: Application tracker..."
python3 tracker.py

echo -e "\n=========================================="
echo "✅ Automation pipeline complete!"
echo "=========================================="