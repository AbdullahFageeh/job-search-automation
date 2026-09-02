#!/usr/bin/env python3
"""
AI Watermark Cleaner — Strip AI provenance marks from job application materials.

Why this matters:
- AI-generated cover letters contain invisible Unicode marks (ZWSP, BIDI, tags)
- PDF/DOCX files can carry C2PA metadata and AI generator tags
- Some ATS systems flag content with AI watermarks
- This tool strips ALL known AI provenance marks before you send

Usage:
    python3 clean_output.py cover_letter.md          # Clean single file
    python3 clean_output.py resumes/                 # Clean all resumes
    python3 clean_output.py scan cover_letter.md      # Inspect only (don't modify)
    python3 clean_output.py clean *.md *.txt          # Clean all markdown/text
    python3 clean_output.py auto                      # Clean all generated files in cover_letters/
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
WM_SCRIPTS = BASE_DIR / "watermarks-remover" / "service" / "scripts"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)
CLEAN_LOG = LOGS_DIR / "cleaned_files.json"


def load_clean_history():
    """Load history of cleaned files."""
    if CLEAN_LOG.exists():
        with open(CLEAN_LOG) as f:
            return json.load(f)
    return []


def save_clean_history(history):
    """Save cleaned files history."""
    with open(CLEAN_LOG, "w") as f:
        json.dump(history, f, indent=2)


def inspect_file(file_path):
    """Scan a file for AI watermarks."""
    result = subprocess.run(
        ["python3", str(WM_SCRIPTS / "inspect_file.py"), str(file_path), "--json"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"raw": result.stdout}
    return {"error": result.stderr or "No output"}


def clean_file(file_path, output_path=None, inplace=False):
    """Clean AI watermarks from a file."""
    cmd = ["python3", str(WM_SCRIPTS / "clean_file.py"), str(file_path)]
    
    if output_path:
        cmd.extend(["-o", str(output_path)])
    elif inplace:
        cmd.append("--in-place")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        report = {"clean": True, "output": result.stdout.strip()}
        if result.stderr:
            report["warnings"] = result.stderr.strip().split("\n")
        return report
    else:
        return {"clean": False, "error": result.stderr or "Unknown error"}


def scan_directory(dir_path):
    """Scan all files in a directory for AI watermarks."""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return {"error": f"Directory not found: {dir_path}"}
    
    results = []
    files = list(dir_path.glob("**/*"))
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    
    print(f"\n🔍 Scanning {len(files)} files in {dir_path}...\n")
    
    for f in files:
        report = inspect_file(f)
        has_marks = report.get("suspicious", False) or report.get("findings", [])
        status = "🚨 HAS MARKS" if has_marks else "✅ Clean"
        print(f"  {status}  {f.relative_to(dir_path)}")
        if has_marks:
            print(f"          {json.dumps(report, indent=2)[:200]}...")
        results.append({"file": str(f), "clean": not has_marks, "report": report})
    
    dirty = sum(1 for r in results if not r["clean"])
    clean = len(results) - dirty
    
    print(f"\n{'='*50}")
    print(f"  Results: {clean} clean, {dirty} need cleaning")
    print(f"{'='*50}")
    
    return results


def clean_directory(dir_path, inplace=False):
    """Clean all files in a directory."""
    dir_path = Path(dir_path)
    if not dir_path.exists():
        return {"error": f"Directory not found: {dir_path}"}
    
    history = load_clean_history()
    cleaned_count = 0
    
    files = list(dir_path.glob("**/*"))
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]
    
    print(f"\n🧹 Cleaning {len(files)} files in {dir_path}...\n")
    
    for f in files:
        # First check if it needs cleaning
        report = inspect_file(f)
        if not report.get("suspicious", False) and not report.get("findings", []):
            print(f"  ✅ Skip (clean)  {f.relative_to(dir_path)}")
            continue
        
        print(f"  🧹 Cleaning... {f.relative_to(dir_path)}")
        result = clean_file(f, inplace=inplace)
        
        if result.get("clean"):
            cleaned_count += 1
            history.append({
                "file": str(f),
                "cleaned_at": datetime.now().isoformat(),
                "result": "success",
            })
            print(f"  ✅ Cleaned")
        else:
            print(f"  ⚠️  Failed: {result.get('error', 'unknown')}")
    
    save_clean_history(history)
    print(f"\n{'='*50}")
    print(f"  🧹 Cleaned {cleaned_count} files")
    print(f"{'='*50}\n")
    
    return {"cleaned": cleaned_count, "total": len(files)}


def pre_send_clean(file_path):
    """Quick clean before sending — inspect + clean if needed."""
    print(f"\n🔍 Inspecting: {file_path}")
    report = inspect_file(file_path)
    
    if not report.get("suspicious", False) and not report.get("findings", []):
        print("  ✅ No AI marks detected — file is clean!\n")
        return True
    
    print(f"  🚨 AI marks found!")
    print(f"  Report: {json.dumps(report, indent=2)[:300]}")
    
    confirm = input("\n  Clean this file? (y/N): ").strip().lower()
    if confirm == 'y':
        result = clean_file(file_path, inplace=True)
        if result.get("clean"):
            print("  ✅ File cleaned!")
            return True
        else:
            print(f"  ❌ Clean failed: {result.get('error')}")
            return False
    else:
        print("  ⏭️  Skipped")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AI Watermark Cleaner for Job Applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan cover_letter.md          Inspect a file for AI marks
  %(prog)s clean cover_letter.md         Clean a file in-place
  %(prog)s clean resumes/                Clean all files in directory
  %(prog)s auto                          Clean all files in cover_letters/
  %(prog)s pre-send cover_letter.md      Quick check before sending
  %(prog)s history                       Show cleaning history
        """
    )
    
    parser.add_argument("action", nargs="?", choices=["scan", "clean", "auto", "pre-send", "history"],
                        default="clean", help="Action to perform")
    parser.add_argument("path", nargs="?", help="File or directory path")
    
    args = parser.parse_args()
    
    if args.action == "scan":
        if not args.path:
            print("❌ Please specify a file or directory to scan")
            sys.exit(1)
        
        p = Path(args.path)
        if p.is_dir():
            scan_directory(p)
        else:
            print(f"\n🔍 Inspecting: {args.path}\n")
            report = inspect_file(p)
            print(json.dumps(report, indent=2))
            if report.get("suspicious"):
                print("\n  🚨 AI marks detected! Run: python3 clean_output.py clean", args.path)
            else:
                print("\n  ✅ No AI marks detected")
    
    elif args.action == "clean":
        if not args.path:
            print("❌ Please specify a file or directory to clean")
            sys.exit(1)
        
        p = Path(args.path)
        if p.is_dir():
            clean_directory(p, inplace=True)
        else:
            print(f"\n🧹 Cleaning: {args.path}")
            result = clean_file(p, inplace=True)
            if result.get("clean"):
                print("  ✅ File cleaned!")
            else:
                print(f"  ❌ Error: {result.get('error')}")
    
    elif args.action == "auto":
        # Clean cover_letters/ and resumes/ directories
        for target in ["cover_letters", "resumes"]:
            target_path = BASE_DIR / target
            if target_path.exists():
                print(f"\n--- Cleaning {target}/ ---")
                clean_directory(target_path, inplace=True)
            else:
                print(f"  ℹ️  {target}/ not found, skipping")
    
    elif args.action == "pre-send":
        if not args.path:
            print("❌ Please specify a file to check before sending")
            sys.exit(1)
        pre_send_clean(Path(args.path))
    
    elif args.action == "history":
        history = load_clean_history()
        if not history:
            print("  No cleaning history yet.")
            return
        
        print(f"\n📜 Cleaning History ({len(history)} entries)\n")
        for entry in history[-10:]:  # Last 10
            print(f"  {entry['cleaned_at'][:19]}  {entry['file']}")
            print(f"      Result: {entry['result']}")
            print()


if __name__ == "__main__":
    main()