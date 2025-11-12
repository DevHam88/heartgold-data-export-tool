import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================
SOURCE_FILENAME = "overlay/overlay_0001.bin"
OUTPUT_FILENAME = "tutors.csv"
LOG_FILENAME = "log_tutors.txt"

START_OFFSET = 0x23AE0  # starting offset of tutor data block
ENTRY_COUNT = 58        # number of tutor moves
BYTES_PER_ENTRY = 4     # 4 bytes per entry (2 for move_id, 1 for cost, 1 for tutor_id)

# ======================================
# Main Function
# ======================================
def read_tutors(file_path):
    with open(file_path, "rb") as f:
        f.seek(START_OFFSET)
        data = f.read(ENTRY_COUNT * BYTES_PER_ENTRY)

        if len(data) < ENTRY_COUNT * BYTES_PER_ENTRY:
            raise ValueError(f"File too short: expected {(ENTRY_COUNT * BYTES_PER_ENTRY)} bytes from offset {START_OFFSET}, got {len(data)}.")

    tutors = []
    for i in range(ENTRY_COUNT):
        start = i * BYTES_PER_ENTRY
        move_id = int.from_bytes(data[start:start+2], "little")
        tutor_cost = data[start+2]
        tutor_id = data[start+3]
        tutors.append((i + 1, move_id, tutor_cost, tutor_id))

    return tutors

# ======================================
# Entry Point
# ======================================
def main():
    parser = argparse.ArgumentParser(description="Export tutor move data from overlay_0001.bin")
    parser.add_argument("--source", required=True, help="Path to the root game data folder")
    parser.add_argument("--output", required=False, help="Output directory path")
    args = parser.parse_args()

    base_path = Path(args.source)
    source_path = base_path / SOURCE_FILENAME

    if not source_path.exists():
        print(f"[ERROR] Source file not found: {source_path}")
        return 1

    output_dir = Path(args.output or "output")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / OUTPUT_FILENAME
    log_file = output_dir / LOG_FILENAME

    try:
        tutors = read_tutors(source_path)
    except Exception as e:
        with open(log_file, "w", encoding="utf-8") as log:
            log.write(f"[ERROR] {e}\n")
        print(f"[ERROR] {e}")
        return 1

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["tutorable_move", "move_id", "tutor_cost", "tutor_id"])
        writer.writerows(tutors)

    # Only create a log if there were issues
    if log_file.exists() and log_file.stat().st_size == 0:
        log_file.unlink()

    print(f"[OK] Export complete: {output_file}")
    return 0


if __name__ == "__main__":
    main()
