import os
import csv
import argparse
from datetime import datetime
from pathlib import Path


# ======================================
# Configuration
# ======================================

SOURCE_FILENAME = "data/a/0/3/3"
OUTPUT_FILENAME = "level_up_learnsets.csv"
LOG_FILENAME = "log_level_up_learnsets.txt"

START_OFFSET = 0x1014
SKIP_FIRST = True  # skip species_id 0

# ======================================
# Helper Functions
# ======================================

def decode_entry(b0, b1):
    """Decode a 2-byte level-up entry."""
    level = b1 // 2
    move_id = b0 + (256 if b1 & 1 else 0)
    return move_id, level


def parse_species_learnset(data, offset, logs):
    """Parse one species learnset block."""
    rows = []
    i = offset
    n = len(data)

    while i + 1 < n:
        b0, b1 = data[i], data[i + 1]

        # Detect terminator patterns (FF FF or FF FF 00 00)
        if b0 == 0xFF and b1 == 0xFF:
            # If followed by optional 00 00, consume those too
            if i + 3 < n and data[i + 2] == 0x00 and data[i + 3] == 0x00:
                i += 4
            else:
                i += 2
            break

        move_id, level = decode_entry(b0, b1)
        rows.append((move_id, level))
        i += 2

    return rows, i


# ======================================
# Main Function
# ======================================

def main():
    parser = argparse.ArgumentParser(description="Export level-up learnsets from ROM contents.")
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

    with open(source_path, "rb") as f:
        f.seek(START_OFFSET)
        data = f.read()

    species_id = 0
    offset = 0
    total_bytes = len(data)

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["species_id", "move_id", "level"])

        while offset < total_bytes:
            rows, new_offset = parse_species_learnset(data, offset, warnings)

            # Always advance offset, even if rows are empty
            if new_offset == offset:
                warnings.append(f"[WARN] Parser did not advance at 0x{offset + START_OFFSET:X}. Aborting.")
                break

            if not (SKIP_FIRST and species_id == 0):
                for move_id, level in rows:
                    writer.writerow([species_id, move_id, level])

            species_id += 1
            offset = new_offset

    # Write log file only if needed
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
