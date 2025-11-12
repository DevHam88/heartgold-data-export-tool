import os
import csv
import argparse
from datetime import datetime
from pathlib import Path


# ======================================
# Configuration
# ======================================

SOURCE_FILENAME = "data/poketool/personal/pms.narc"
OUTPUT_FILENAME = "offspring.csv"
LOG_FILENAME = "log_offspring.txt"

START_OFFSET = 0x0
SKIP_FIRST = True  # skip species_id 0

# ======================================
# Main Function
# ======================================

def main():
    parser = argparse.ArgumentParser(description="Export offspring species data from ROM contents.")
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

    warnings = []

    # Read the full file
    data = Path(source_path).read_bytes()

    if len(data) % 2 != 0:
        warnings.append(f"[WARN] File size ({len(data)} bytes) is not divisible by 2. Data may be corrupted.")

    total_species = len(data) // 2
    expected_bytes = total_species * 2

    # Create the CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["species_id", "offspring_species_id"])

        for i in range(total_species):
            start = i * 2
            offspring_id = int.from_bytes(data[start:start + 2], "little")

            if not (SKIP_FIRST and i == 0):
                writer.writerow([i, offspring_id])

    # Warn if extra data remain (possible in modified ROMs)
    if len(data) > expected_bytes:
        extra = len(data) - expected_bytes
        warnings.append(f"[WARN] Extra {extra} bytes found beyond expected data range.")

    # Write log only if needed
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
