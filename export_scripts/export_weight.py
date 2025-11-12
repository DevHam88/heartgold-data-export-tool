import os
import csv
import argparse
from datetime import datetime
from pathlib import Path


# ======================================
# Configuration
# ======================================

SOURCE_FILENAME = "data/a/2/1/4"
OUTPUT_FILENAME = "weight.csv"
LOG_FILENAME = "log_weight.txt"

START_OFFSET = 0xB1C
TOTAL_EXPECTED_SPECIES = 494
SKIP_FIRST = True  # skip species_id 0

# ======================================
# Main Function
# ======================================

def main():
    parser = argparse.ArgumentParser(description="Export species weight data from ROM contents.")
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

    # Read relevant bytes
    with open(source_path, "rb") as f:
        f.seek(START_OFFSET)
        data = f.read(TOTAL_EXPECTED_SPECIES * 4)

    if len(data) < TOTAL_EXPECTED_SPECIES * 4:
        warnings.append(
            f"[WARN] Expected {TOTAL_EXPECTED_SPECIES * 4} bytes but found only {len(data)} from offset 0x{START_OFFSET:X}."
        )

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["species_id", "weight"])

        species_count = min(TOTAL_EXPECTED_SPECIES, len(data) // 4)

        for i in range(species_count):
            start = i * 4
            weight_bytes = data[start:start + 2]
            padding_bytes = data[start + 2:start + 4]

            weight = int.from_bytes(weight_bytes, "little")

            # Validate padding (should be 00 00)
            if padding_bytes != b"\x00\x00":
                warnings.append(
                    f"[WARN] Non-zero padding ({padding_bytes.hex(' ').upper()}) at species_id {i}."
                )

            if not (SKIP_FIRST and i == 0):
                writer.writerow([i, weight])

    # Write log file only if warnings exist
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
