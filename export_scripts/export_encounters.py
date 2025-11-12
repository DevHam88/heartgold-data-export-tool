# export_encounters.py
# Reads encounter sets from two binaries (HG/SS), starting at a fixed offset.
# Each encounter set is 196 bytes and follows a fixed field pattern (below).
# Outputs two CSVs (HG/SS). Logs warnings/errors to log_encounters.txt.

import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
SOURCE_1_FILENAME = "data/a/0/3/7"   # HeartGold
SOURCE_2_FILENAME = "data/a/1/3/6"   # SoulSilver
OUTPUT_1_FILENAME = "encounters_hg.csv"
OUTPUT_2_FILENAME = "encounters_ss.csv"
LOG_FILENAME      = "log_encounters.txt"

START_OFFSET      = 0x4A4            # start of encounter data
RECORD_SIZE       = 196              # bytes per encounter set

# Field pattern (hardcoded from your encounterset_data_pattern.csv).
# Sum of sizes must equal RECORD_SIZE. 'PADDING' is validated as zeros and omitted from CSV.
FIELD_DEFS = [
    {'name': 'walk_rate', 'size': 1},
    {'name': 'surf_rate', 'size': 1},
    {'name': 'rock_smash_rate', 'size': 1},
    {'name': 'old_rod_rate', 'size': 1},
    {'name': 'good_rod_rate', 'size': 1},
    {'name': 'super_rod_rate', 'size': 1},
    {'name': 'PADDING', 'size': 2},

    # Walk slots levels (12)
    {'name': 'walk_slot_01_level', 'size': 1},
    {'name': 'walk_slot_02_level', 'size': 1},
    {'name': 'walk_slot_03_level', 'size': 1},
    {'name': 'walk_slot_04_level', 'size': 1},
    {'name': 'walk_slot_05_level', 'size': 1},
    {'name': 'walk_slot_06_level', 'size': 1},
    {'name': 'walk_slot_07_level', 'size': 1},
    {'name': 'walk_slot_08_level', 'size': 1},
    {'name': 'walk_slot_09_level', 'size': 1},
    {'name': 'walk_slot_10_level', 'size': 1},
    {'name': 'walk_slot_11_level', 'size': 1},
    {'name': 'walk_slot_12_level', 'size': 1},

    # Walk slots species (12 x u16 LE)
    {'name': 'walk_slot_01_species', 'size': 2},
    {'name': 'walk_slot_02_species', 'size': 2},
    {'name': 'walk_slot_03_species', 'size': 2},
    {'name': 'walk_slot_04_species', 'size': 2},
    {'name': 'walk_slot_05_species', 'size': 2},
    {'name': 'walk_slot_06_species', 'size': 2},
    {'name': 'walk_slot_07_species', 'size': 2},
    {'name': 'walk_slot_08_species', 'size': 2},
    {'name': 'walk_slot_09_species', 'size': 2},
    {'name': 'walk_slot_10_species', 'size': 2},
    {'name': 'walk_slot_11_species', 'size': 2},
    {'name': 'walk_slot_12_species', 'size': 2},

    # Surf slots (5): min, max, species
    {'name': 'surf_slot_01_min_level', 'size': 1},
    {'name': 'surf_slot_01_max_level', 'size': 1},
    {'name': 'surf_slot_01_species',   'size': 2},
    {'name': 'surf_slot_02_min_level', 'size': 1},
    {'name': 'surf_slot_02_max_level', 'size': 1},
    {'name': 'surf_slot_02_species',   'size': 2},
    {'name': 'surf_slot_03_min_level', 'size': 1},
    {'name': 'surf_slot_03_max_level', 'size': 1},
    {'name': 'surf_slot_03_species',   'size': 2},
    {'name': 'surf_slot_04_min_level', 'size': 1},
    {'name': 'surf_slot_04_max_level', 'size': 1},
    {'name': 'surf_slot_04_species',   'size': 2},
    {'name': 'surf_slot_05_min_level', 'size': 1},
    {'name': 'surf_slot_05_max_level', 'size': 1},
    {'name': 'surf_slot_05_species',   'size': 2},

    # Old Rod slots (5)
    {'name': 'old_rod_slot_01_min_level', 'size': 1},
    {'name': 'old_rod_slot_01_max_level', 'size': 1},
    {'name': 'old_rod_slot_01_species',   'size': 2},
    {'name': 'old_rod_slot_02_min_level', 'size': 1},
    {'name': 'old_rod_slot_02_max_level', 'size': 1},
    {'name': 'old_rod_slot_02_species',   'size': 2},
    {'name': 'old_rod_slot_03_min_level', 'size': 1},
    {'name': 'old_rod_slot_03_max_level', 'size': 1},
    {'name': 'old_rod_slot_03_species',   'size': 2},
    {'name': 'old_rod_slot_04_min_level', 'size': 1},
    {'name': 'old_rod_slot_04_max_level', 'size': 1},
    {'name': 'old_rod_slot_04_species',   'size': 2},
    {'name': 'old_rod_slot_05_min_level', 'size': 1},
    {'name': 'old_rod_slot_05_max_level', 'size': 1},
    {'name': 'old_rod_slot_05_species',   'size': 2},

    # Good Rod slots (5)
    {'name': 'good_rod_slot_01_min_level', 'size': 1},
    {'name': 'good_rod_slot_01_max_level', 'size': 1},
    {'name': 'good_rod_slot_01_species',   'size': 2},
    {'name': 'good_rod_slot_02_min_level', 'size': 1},
    {'name': 'good_rod_slot_02_max_level', 'size': 1},
    {'name': 'good_rod_slot_02_species',   'size': 2},
    {'name': 'good_rod_slot_03_min_level', 'size': 1},
    {'name': 'good_rod_slot_03_max_level', 'size': 1},
    {'name': 'good_rod_slot_03_species',   'size': 2},
    {'name': 'good_rod_slot_04_min_level', 'size': 1},
    {'name': 'good_rod_slot_04_max_level', 'size': 1},
    {'name': 'good_rod_slot_04_species',   'size': 2},
    {'name': 'good_rod_slot_05_min_level', 'size': 1},
    {'name': 'good_rod_slot_05_max_level', 'size': 1},
    {'name': 'good_rod_slot_05_species',   'size': 2},

    # Super Rod slots (5)
    {'name': 'super_rod_slot_01_min_level', 'size': 1},
    {'name': 'super_rod_slot_01_max_level', 'size': 1},
    {'name': 'super_rod_slot_01_species',   'size': 2},
    {'name': 'super_rod_slot_02_min_level', 'size': 1},
    {'name': 'super_rod_slot_02_max_level', 'size': 1},
    {'name': 'super_rod_slot_02_species',   'size': 2},
    {'name': 'super_rod_slot_03_min_level', 'size': 1},
    {'name': 'super_rod_slot_03_max_level', 'size': 1},
    {'name': 'super_rod_slot_03_species',   'size': 2},
    {'name': 'super_rod_slot_04_min_level', 'size': 1},
    {'name': 'super_rod_slot_04_max_level', 'size': 1},
    {'name': 'super_rod_slot_04_species',   'size': 2},
    {'name': 'super_rod_slot_05_min_level', 'size': 1},
    {'name': 'super_rod_slot_05_max_level', 'size': 1},
    {'name': 'super_rod_slot_05_species',   'size': 2},

    # Special species flags (u16 LE each)
    {'name': 'walk_swarm_species', 'size': 2},
    {'name': 'surf_swarm_species', 'size': 2},
    {'name': 'rod_night_species',  'size': 2},
    {'name': 'rod_swarm_species',  'size': 2},
]

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)

def write_log_line(log_lines, msg):
    log_lines.append(msg)

def le_int(b: bytes) -> int:
    # Interpret 1- or 2-byte little-endian chunks as unsigned integers
    if len(b) == 1:
        return b[0]
    elif len(b) == 2:
        return int.from_bytes(b, 'little', signed=False)
    # Fallback: bigger chunks shouldn’t occur here; treat as hex string if needed
    return int.from_bytes(b, 'little', signed=False)

def parse_record(block: bytes, set_index: int, log_lines) -> dict:
    out = {}
    pos = 0
    for f in FIELD_DEFS:
        name = f['name']
        size = f['size']
        chunk = block[pos:pos+size]
        if len(chunk) != size:
            write_log_line(log_lines, f"[ERROR] Truncated field '{name}' in set {set_index} at byte {pos}.")
            return None
        if name == "PADDING":
            if any(chunk):  # not all zeros
                write_log_line(log_lines, f"[WARN] Non-zero padding at set {set_index} (bytes={chunk.hex(' ')}).")
        else:
            out[name] = le_int(chunk)
        pos += size
    return out

def process_file(source_root: Path, rel_source: str, output_csv: Path, log_file: Path) -> bool:
    log_lines = []
    source_path = (source_root / rel_source)
    if not source_path.exists():
        write_log_line(log_lines, f"[ERROR] Source file not found: {rel_source}")
        # Only write a log if there’s something in it
        if log_lines:
            ensure_parent(log_file)
            with log_file.open("a", encoding="utf-8", newline="") as lf:
                for line in log_lines:
                    lf.write(line + "\n")
        print(f"[FAIL] {rel_source} not found.")
        return False

    data = source_path.read_bytes()
    if len(data) < START_OFFSET:
        write_log_line(log_lines, f"[ERROR] File shorter than START_OFFSET: {rel_source}")
        if log_lines:
            ensure_parent(log_file)
            with log_file.open("a", encoding="utf-8", newline="") as lf:
                for line in log_lines:
                    lf.write(line + "\n")
        print(f"[FAIL] {rel_source} is too small.")
        return False

    payload = data[START_OFFSET:]
    if len(payload) % RECORD_SIZE != 0:
        write_log_line(
            log_lines,
            f"[WARN] Data length ({len(payload)}) not multiple of {RECORD_SIZE} in {rel_source}. "
            f"Ignoring trailing {len(payload)%RECORD_SIZE} byte(s)."
        )
        payload = payload[: len(payload) - (len(payload) % RECORD_SIZE)]

    sets = len(payload) // RECORD_SIZE

    rows = []
    for i in range(sets):
        block = payload[i*RECORD_SIZE : (i+1)*RECORD_SIZE]
        parsed = parse_record(block, i, log_lines)
        if parsed is None:
            write_log_line(log_lines, f"[ERROR] Aborting parse for {rel_source} at set {i}.")
            break
        parsed_row = {'encounterset_id': i}
        parsed_row.update(parsed)
        rows.append(parsed_row)

    # Write CSV
    if rows:
        ensure_parent(output_csv)
        fieldnames = ['encounterset_id'] + [f['name'] for f in FIELD_DEFS if f['name'] != 'PADDING']
        with output_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[OK] Export complete: {output_csv}")
    else:
        print(f"[FAIL] No rows parsed: {rel_source}")

    # Write any logs captured (append mode, one script-wide log)
    if log_lines:
        ensure_parent(log_file)
        with log_file.open("a", encoding="utf-8", newline="") as lf:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            lf.write(f"--- {timestamp} | {rel_source} ---\n")
            for line in log_lines:
                lf.write(line + "\n")

    return bool(rows)

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Export encounter sets (HG & SS) to CSV.")
    parser.add_argument("--source", required=True, help="Top-level ROM contents folder.")
    parser.add_argument("--output", required=False, help="Output folder (timestamped if not provided).")
    args = parser.parse_args()

    source_root = Path(args.source)
    if not source_root.exists():
        print(f"[FAIL] Source folder not found: {source_root}")
        return 1

    # Timestamped output folder if not provided
    if args.output:
        out_root = Path(args.output)
    else:
        out_root = Path("output") / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    out_root.mkdir(parents=True, exist_ok=True)

    log_path = out_root / LOG_FILENAME
    # Don’t create an empty log; append messages only when needed.

    ok1 = process_file(source_root, SOURCE_1_FILENAME, out_root / OUTPUT_1_FILENAME, log_path)
    ok2 = process_file(source_root, SOURCE_2_FILENAME, out_root / OUTPUT_2_FILENAME, log_path)

    if ok1 and ok2:
        print("[OK] Both HG and SS encounters exported.")
        return 0
    elif ok1 or ok2:
        print("[OK] Partial export completed (one version). See log for details." if log_path.exists() else "[OK] Partial export completed.")
        return 0
    else:
        print("[FAIL] No encounters exported.")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
