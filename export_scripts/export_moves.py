import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================
SOURCE_FILENAME = "data/a/0/1/1"
OUTPUT_FILENAME = "moves.csv"
LOG_FILENAME = "log_moves.txt"

START_OFFSET = 0xEEC  # starting offset for move_id 0
SKIP_FIRST = True  # skip move_id 0

# ======================================
# Main Function
# ======================================
def parse_move_entry(data, move_id):
    move_effect = int.from_bytes(data[0:2], "little")
    category = data[2]
    power = data[3]
    move_type = data[4]
    accuracy = data[5]
    pp = data[6]
    side_effect_rate = data[7]
    range_flags = int.from_bytes(data[8:10], "little")
    priority = data[10] if data[10] <= 10 else data[10] - 256
    flags = data[11]
    contest_appeal = data[12]
    contest_condition = data[13]
    padding = data[14:16]

    warning = None
    if padding != b"\x00\x00":
        warning = f"[WARN] Padding not 00 00 for move_id {move_id}"

    return {
        "move_id": move_id,
        "move_effect_script_id": move_effect,
        "category": category,
        "power": power,
        "type": move_type,
        "accuracy": accuracy,
        "power_points": pp,
        "side_effect_rate": side_effect_rate,
        "range": range_flags,
        "priority": priority,
        "contest_appeal": contest_appeal,
        "contest_condition": contest_condition,
    }, warning

# ======================================
# Entry Point
# ======================================
def main():
    parser = argparse.ArgumentParser(description="Export move data from ROM contents.")
    parser.add_argument("--source", required=True, help="Path to ROM contents directory")
    parser.add_argument("--output", default=None, help="Output directory (default: ./output/<timestamp>)")
    args = parser.parse_args()

    # Determine output folder (timestamped if not provided)
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_dir = Path("output") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_path = Path(args.source) / SOURCE_FILENAME
    output_file = output_dir / OUTPUT_FILENAME
    log_file = output_dir / LOG_FILENAME

    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}")
        return 1

    with open(source_path, "rb") as f:
        data = f.read()[START_OFFSET:]

    warnings = []

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "move_id", "move_effect_script_id", "category", "power", "type",
            "accuracy", "power_points", "side_effect_rate", "range", "priority",
            "contest_appeal", "contest_condition"
        ])
        writer.writeheader()

        move_size = 16
        for move_id in range(0, len(data) // move_size):
            if SKIP_FIRST and move_id == 0:
                continue
            entry_data = data[move_id * move_size:(move_id + 1) * move_size]
            parsed, warning = parse_move_entry(entry_data, move_id)
            writer.writerow(parsed)
            if warning:
                warnings.append(warning)

    # Only create log if warnings exist
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    exit(main())
