import os
import subprocess
from datetime import datetime
import argparse

WORKERS = ["export_personal_data.py","export_evolutions.py","export_weight.py","export_offspring.py","export_moves.py","export_level_up_learnsets.py","export_egg_learnsets.py","export_tutors.py","export_tutor_learnsets.py","export_encounters.py","export_trainers.py","export_constants.py"]
OUTPUT_ROOT = "output"
SUMMARY_FILENAME = "export_summary.txt"

def run_worker(script_name, source, output_folder):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    cmd = ["python", script_path, "--source", source, "--output", output_folder]

    print(f"\n> Running {script_name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout.strip())

    status = "[OK] SUCCESS" if result.returncode == 0 else "[X] FAILED"
    warnings_file = [f for f in os.listdir(output_folder) if f.startswith("warnings_")]

    if warnings_file:
        print(f"[!] Warning file(s): {', '.join(warnings_file)}")

    if result.stderr.strip():
        print(f"STDERR:\n{result.stderr.strip()}")

    return {
        "script": script_name,
        "status": status,
        "warnings": warnings_file,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

def write_summary(results, output_folder, source_path):
    summary_path = os.path.join(output_folder, SUMMARY_FILENAME)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=== Export Summary ===\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Source folder: {source_path}\n\n")

        for r in results:
            f.write(f"{r['script']}: {r['status']}\n")
            if r["warnings"]:
                f.write(f"  Warnings: {', '.join(r['warnings'])}\n")
            if r["stderr"]:
                f.write(f"  STDERR:\n    {r['stderr'].replace(os.linesep, os.linesep + '    ')}\n")
        f.write("\nAll exports complete.\n")

    print(f"[OK] Summary written to: {summary_path}")

def main():
    parser = argparse.ArgumentParser(description="Run all export scripts sequentially.")
    parser.add_argument("--source", required=True, help="Path to ROM contents root folder.")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_folder = os.path.join(OUTPUT_ROOT, timestamp)
    os.makedirs(output_folder, exist_ok=True)

    print(f"\n=== Starting Data Export ===")
    print(f"Source folder: {args.source}")
    print(f"Output folder: {output_folder}\n")

    results = []

    for worker in WORKERS:
        results.append(run_worker(worker, args.source, output_folder))

    write_summary(results, output_folder, args.source)

    print("\n=== Export Summary ===")
    for r in results:
        print(f"{r['script']}: {r['status']}")
    print(f"\nAll exports complete. Outputs saved to:\n{output_folder}\n")

if __name__ == "__main__":
    main()
