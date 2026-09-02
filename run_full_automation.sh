#!/bin/bash
# Full Automation Run Script
# Usage: ./run_full_automation.sh [num_jobs_to_apply]

cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 FULL JOB SEARCH AUTOMATION PIPELINE"
echo "=========================================="

NUM_JOBS=${1:-10}

# 1. Scan for entry-level jobs
echo -e "\n📋 Step 1: Scanning LinkedIn for entry-level jobs..."
python3 entry_level_jobs.py scan

# 2. Scan other boards
echo -e "\n📋 Step 2: Scanning other job boards..."
python3 other_boards_monitor.py once

# 3. Show application tracker
echo -e "\n📋 Step 3: Application tracker..."
python3 tracker.py

# 4. ATS optimization report
echo -e "\n📋 Step 4: ATS Resume Optimization..."
python3 ats_optimizer.py

# 5. Generate daily digest
echo -e "\n📋 Step 5: Generating daily digest..."
python3 daily_digest.py

echo -e "\n=========================================="
echo "✅ Automation pipeline complete!"
echo "=========================================="
