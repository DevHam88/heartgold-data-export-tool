import os
import csv
import argparse
from datetime import datetime
from pathlib import Path


# ======================================
# Configuration
# ======================================

SOURCE_FILENAME = "data/a/2/2/9"
OUTPUT_FILENAME = "egg_learnsets.csv"
LOG_FILENAME = "log_egg_learnsets.txt"

START_OFFSET = 0x3C  # skip NARC header data
MAX_MOVES = 16       # max egg moves per species


# ======================================
# Helper Function
# ======================================

def read_u16_le(f):
    """Read a 2-byte little-endian unsigned integer."""
    b = f.read(2)
    return int.from_bytes(b, "little") if b else None


# ======================================
# Main Function
# ======================================

def main():
    parser = argparse.ArgumentParser(description="Export egg learnsets from ROM contents.")
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
    learnsets = []

    with open(source_path, "rb") as f:
        f.seek(START_OFFSET)
        current_species = None
        current_moves = []

        while True:
            num = read_u16_le(f)
            if num is None:
                break
            if num == 0xFFFF:
                break

            if num >= 20000:
                # Save previous species if one was active
                if current_species is not None:
                    if len(current_moves) > MAX_MOVES:
                        warnings.append(
                            f"[WARN] Species {current_species} has {len(current_moves)} egg moves (max {MAX_MOVES})"
                        )
                    # Pad or trim moves
                    row = [current_species] + current_moves[:MAX_MOVES]
                    row += [""] * (MAX_MOVES - len(row) + 1)
                    learnsets.append(row)

                # Start new species
                current_species = num - 20000
                current_moves = []
            else:
                # Regular move ID
                current_moves.append(num)

        # Save last species
        if current_species is not None:
            if len(current_moves) > MAX_MOVES:
                warnings.append(
                    f"[WARN] Species {current_species} has {len(current_moves)} egg moves (max {MAX_MOVES})"
                )
            row = [current_species] + current_moves[:MAX_MOVES]
            row += [""] * (MAX_MOVES - len(row) + 1)
            learnsets.append(row)

    # Write CSV
    headers = ["species_id"] + [f"egg_move_{i:02d}" for i in range(1, MAX_MOVES + 1)]
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(learnsets)

    # Write log only if there are warnings
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
