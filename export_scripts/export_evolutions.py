import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================
SOURCE_FILENAME = "data/a/0/3/4"
OUTPUT_FILENAME = "evolutions.csv"
LOG_FILENAME = "log_evolutions.txt"

START_OFFSET = 0x1014  # starting offset for evolution data
TOTAL_EXPECTED_SPECIES = 508  # total number of species to process
EVO_METHODS_PER_SPECIES = 7  # evolution slots per species
SKIP_FIRST = True  # skip species_id 0

# ======================================
# Main Function
# ======================================
def parse_evolution_entry(data):
    """Parse a 6-byte evolution entry (method, parameter, target species)."""
    method = int.from_bytes(data[0:2], "little")
    param = int.from_bytes(data[2:4], "little")
    target = int.from_bytes(data[4:6], "little")
    return method, param, target

# ======================================
# Entry Point
# ======================================
def main():
    parser = argparse.ArgumentParser(description="Export evolution data from ROM contents.")
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
        f.seek(START_OFFSET)
        data = f.read()

    bytes_per_species = EVO_METHODS_PER_SPECIES * 6 + 2
    expected_length = TOTAL_EXPECTED_SPECIES * bytes_per_species
    actual_length = len(data)

    warnings = []
    if actual_length != expected_length:
        warnings.append(f"[WARN] Data length mismatch: expected {expected_length} bytes, got {actual_length}")

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "species_id", "evolution_method", "evolution_parameter", "target_species_id"
        ])
        writer.writeheader()

        for species_id in range(TOTAL_EXPECTED_SPECIES):
            if SKIP_FIRST and species_id == 0:
                continue

            offset = species_id * bytes_per_species
            species_data = data[offset:offset + bytes_per_species - 2]  # skip padding

            for i in range(0, len(species_data), 6):
                method, param, target = parse_evolution_entry(species_data[i:i+6])
                if method == 0 and param == 0 and target == 0:
                    continue
                writer.writerow({
                    "species_id": species_id,
                    "evolution_method": method,
                    "evolution_parameter": param,
                    "target_species_id": target
                })

    # Only create log if warnings exist
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    exit(main())
