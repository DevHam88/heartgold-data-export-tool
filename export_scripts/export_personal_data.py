import os
import csv
import argparse
from datetime import datetime
from pathlib import Path


# ======================================
# Configuration
# ======================================

SOURCE_FILENAME = "data/a/0/0/2"
OUTPUT_1_FILENAME = "personal_data.csv"
OUTPUT_2_FILENAME = "machine_learnsets.csv"
LOG_FILENAME = "log_personal_data.txt"

START_OFFSET = 0x1014  # starting offset for packed NARC file
SKIP_FIRST = True  # skip species_id 0
BYTES_PER_SPECIES = 44  # bytes per species entry


# ======================================
# Helper Functions
# ======================================

def parse_ev_yield(data):
    """Decode the 2-byte EV yield value into its 6 component stats."""
    ev_yield = int.from_bytes(data, "little")
    return {
        "ev_yield_hp": ((ev_yield >> 8) & 1) + ((ev_yield >> 9) & 1) * 2,
        "ev_yield_atk": ((ev_yield >> 10) & 1) + ((ev_yield >> 11) & 1) * 2,
        "ev_yield_def": ((ev_yield >> 12) & 1) + ((ev_yield >> 13) & 1) * 2,
        "ev_yield_spd": ((ev_yield >> 14) & 1) + ((ev_yield >> 15) & 1) * 2,
        "ev_yield_spatk": (ev_yield & 1) + ((ev_yield >> 1) & 1) * 2,
        "ev_yield_spdef": ((ev_yield >> 2) & 1) + ((ev_yield >> 3) & 1) * 2,
    }


def parse_personal_entry(data, species_id):
    """Parse the first 44 bytes of a species record into structured fields."""
    fields = {
        "species_id": species_id,
        "base_stat_hp": data[0],
        "base_stat_atk": data[1],
        "base_stat_def": data[2],
        "base_stat_spd": data[3],
        "base_stat_spatk": data[4],
        "base_stat_spdef": data[5],
        "type_1": data[6],
        "type_2": data[7],
        "catch_rate": data[8],
        "base_exp_yield": data[9],
        "held_item_1": int.from_bytes(data[12:14], "little"),
        "held_item_2": int.from_bytes(data[14:16], "little"),
        "gender_ratio": data[16],
        "hatch_steps_rate": data[17],
        "base_friendship": data[18],
        "growth_rate": data[19],
        "egg_group_1": data[20],
        "egg_group_2": data[21],
        "ability_1": data[22],
        "ability_2": data[23],
        "flee_rate": data[24],
        "colour": data[25],
    }
    fields.update(parse_ev_yield(data[10:12]))
    return fields


def decode_machine_learnset(data):
    """Decode the 100-bit machine learnset section into a list of 0/1 flags."""
    bits = int.from_bytes(data, "little")
    return [(bits >> i) & 1 for i in range(100)]


# ======================================
# Main Function
# ======================================

def main():
    parser = argparse.ArgumentParser(description="Export personal and machine learnset data from ROM contents.")
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
    output_1 = output_dir / OUTPUT_1_FILENAME
    output_2 = output_dir / OUTPUT_2_FILENAME
    log_file = output_dir / LOG_FILENAME

    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}")
        return 1

    warnings = []

    with open(source_path, "rb") as f:
        f.seek(START_OFFSET)
        data = f.read()

    species_size = BYTES_PER_SPECIES
    total_species = len(data) // species_size

    with open(output_1, "w", newline="", encoding="utf-8") as csv1, \
         open(output_2, "w", newline="", encoding="utf-8") as csv2:

        # Writer for personal data
        personal_writer = csv.DictWriter(csv1, fieldnames=[
            "species_id", "base_stat_hp", "base_stat_atk", "base_stat_def",
            "base_stat_spd", "base_stat_spatk", "base_stat_spdef",
            "type_1", "type_2", "catch_rate", "base_exp_yield",
            "ev_yield_hp", "ev_yield_atk", "ev_yield_def", "ev_yield_spd",
            "ev_yield_spatk", "ev_yield_spdef",
            "held_item_1", "held_item_2",
            "gender_ratio", "hatch_steps_rate", "base_friendship",
            "growth_rate", "egg_group_1", "egg_group_2",
            "ability_1", "ability_2", "flee_rate", "colour"
        ])
        personal_writer.writeheader()

        # Writer for machine learnsets (wide format: 0/1 flags per machine)
        machine_fieldnames = ["species_id"] + [f"machine_{i:03d}" for i in range(1, 101)]
        machine_writer = csv.DictWriter(csv2, fieldnames=machine_fieldnames)
        machine_writer.writeheader()

        for i in range(total_species):
            species_id = i
            if SKIP_FIRST and i == 0:
                continue

            start = i * species_size
            entry_data = data[start:start + species_size]
            if len(entry_data) < species_size:
                warnings.append(f"[WARN] Incomplete data for species_id {species_id}")
                continue

            # Write personal data
            personal_writer.writerow(parse_personal_entry(entry_data, species_id))

            # Write machine learnset data
            learnset_bits = decode_machine_learnset(entry_data[28:44])
            row = {"species_id": species_id}
            for idx, bit in enumerate(learnset_bits, start=1):
                row[f"machine_{idx:03d}"] = bit
            machine_writer.writerow(row)

    # Only create a log if there were issues
    if warnings:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("\n".join(warnings))
        print(f"[WARN] {len(warnings)} issue(s) written to {log_file}")

    print(f"[OK] Export complete: {output_1}")
    print(f"[OK] Export complete: {output_2}")
    return 0


if __name__ == "__main__":
    main()
