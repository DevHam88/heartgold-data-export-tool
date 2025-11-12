import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================
SOURCE_FILENAME = "data/fielddata/wazaoshie/waza_oshie.bin"
OUTPUT_FILENAME = "tutor_learnsets.csv"
LOG_FILENAME = "log_tutor_learnsets.txt"

BYTES_PER_SPECIES = 8  # total bytes sequentially for each species
TUTORABLE_MOVE_COUNT = 58  # Max qty tutorable moves
MISSING_SPECIES = [494, 495]  # Egg and Bad Egg


# ======================================
# Main Function
# ======================================
def parse_tutor_learnsets(data: bytes):
    total_entries = len(data) // BYTES_PER_SPECIES
    results = []
    log_lines = []

    if len(data) % BYTES_PER_SPECIES != 0:
        log_lines.append(
            f"[WARN] File length ({len(data)} bytes) is not a multiple of {BYTES_PER_SPECIES}. "
            "Possible corruption or unexpected data size."
        )

    species_id = 1
    for i in range(total_entries):
        # Skip all missing species IDs before processing this entry
        while species_id in MISSING_SPECIES:
            species_id += 1

        start = i * BYTES_PER_SPECIES
        entry = data[start:start + BYTES_PER_SPECIES]

        # Convert each byte into 8 bits (LSB-first)
        bits = []
        for byte in entry:
            bits.extend([(byte >> b) & 1 for b in range(8)])

        bits = bits[:TUTORABLE_MOVE_COUNT]
        results.append([species_id] + bits)
        species_id += 1

    log_lines.append(
        "[INFO] Adjusted for missing Egg and Bad Egg entries (species 494–495). "
        "Output species IDs aligned correctly."
    )

    return results, log_lines


# ======================================
# Entry Point
# ======================================
def main():
    parser = argparse.ArgumentParser(description="Export tutor learnsets from ROM contents.")
    parser.add_argument("--source", required=True, help="Path to ROM contents root (folder containing 'data').")
    parser.add_argument("--output", default=None, help="Output directory (default: ./output/<timestamp>).")
    args = parser.parse_args()

    # Timestamped output folder
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
        data = f.read()

    results, log_lines = parse_tutor_learnsets(data)

    # Write main CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        header = ["species_id"] + [f"tutorable_move_{i+1:02d}" for i in range(TUTORABLE_MOVE_COUNT)]
        writer.writerow(header)
        writer.writerows(results)

    # Write logs
    if log_lines:
        with open(log_file, "w", encoding="utf-8") as lfile:
            lfile.write("\n".join(log_lines))
        print(f"[INFO] {len(log_lines)} note(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
