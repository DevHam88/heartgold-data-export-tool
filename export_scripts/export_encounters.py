import os
import csv
import argparse
from datetime import datetime
from pathlib import Path

# Configuration
SOURCE_1_FILENAME = "data/a/0/3/7"
SOURCE_2_FILENAME = "data/a/1/3/6"

OUTPUT_1_FILENAME = "encounters_hg.csv"
OUTPUT_2_FILENAME = "encounters_ss.csv"

LOG_FILENAME = "log_encounters.txt"

START_OFFSET = 0x4A4
BLOCK_SIZE = 196  # bytes per encounter set

# Data contract (hardcoded)
# Notes:
# - "skip": consume bytes but do not output columns
# - "repeat": repeats a structure N times with 1-based slot numbering
CONTRACT = [
    {"name": "rates", "type": "u8", "count": 6,
     "columns": ["walk_rate", "surf_rate", "rock_smash_rate", "old_rod_rate", "good_rod_rate", "super_rod_rate"]},
    {"name": "padding", "type": "u8", "count": 2, "skip": True, "validate_zero": True},

    {"name": "walk_levels", "type": "u8", "count": 12,
     "columns": [f"walk_slot_{i:02d}_level" for i in range(1, 13)]},

    {"name": "walk_morning_species", "type": "u16le", "count": 12,
     "columns": [f"walk_morning_slot_{i:02d}_species" for i in range(1, 13)]},
    {"name": "walk_day_species", "type": "u16le", "count": 12,
     "columns": [f"walk_day_slot_{i:02d}_species" for i in range(1, 13)]},
    {"name": "walk_night_species", "type": "u16le", "count": 12,
     "columns": [f"walk_night_slot_{i:02d}_species" for i in range(1, 13)]},

    {"name": "radio_species", "type": "u16le", "count": 4,
     "columns": [f"radio_slot_{i:02d}_species" for i in range(1, 5)]},

    # surf slots (5): min_level(u8), max_level(u8), species(u16le)
    {"name": "surf_slots", "repeat": 5, "column_prefix": "surf_slot_",
     "structure": [
         {"name": "min_level", "type": "u8", "column_suffix": "_min_level"},
         {"name": "max_level", "type": "u8", "column_suffix": "_max_level"},
         {"name": "species", "type": "u16le", "column_suffix": "_species"},
     ]},

    # rock smash slots (2): min_level(u8), max_level(u8), species(u16le)
    {"name": "rock_smash_slots", "repeat": 2, "column_prefix": "rock_smash_slot_",
     "structure": [
         {"name": "min_level", "type": "u8", "column_suffix": "_min_level"},
         {"name": "max_level", "type": "u8", "column_suffix": "_max_level"},
         {"name": "species", "type": "u16le", "column_suffix": "_species"},
     ]},

    # rods (old/good/super) slots (5 each): min_level(u8), max_level(u8), species(u16le)
    {"name": "old_rod_slots", "repeat": 5, "column_prefix": "old_rod_slot_",
     "structure": [
         {"name": "min_level", "type": "u8", "column_suffix": "_min_level"},
         {"name": "max_level", "type": "u8", "column_suffix": "_max_level"},
         {"name": "species", "type": "u16le", "column_suffix": "_species"},
     ]},
    {"name": "good_rod_slots", "repeat": 5, "column_prefix": "good_rod_slot_",
     "structure": [
         {"name": "min_level", "type": "u8", "column_suffix": "_min_level"},
         {"name": "max_level", "type": "u8", "column_suffix": "_max_level"},
         {"name": "species", "type": "u16le", "column_suffix": "_species"},
     ]},
    {"name": "super_rod_slots", "repeat": 5, "column_prefix": "super_rod_slot_",
     "structure": [
         {"name": "min_level", "type": "u8", "column_suffix": "_min_level"},
         {"name": "max_level", "type": "u8", "column_suffix": "_max_level"},
         {"name": "species", "type": "u16le", "column_suffix": "_species"},
     ]},

    # swarm/night species
    {"name": "swarm_species_1", "type": "u16le", "count": 2,
     "columns": ["swarm_walk_slot_species", "swarm_surf_slot_species"]},
    {"name": "night_species", "type": "u16le", "count": 1,
     "columns": ["night_fishing_species"]},
    {"name": "swarm_species_2", "type": "u16le", "count": 1,
     "columns": ["swarm_rod_slot_species"]},
]


def _read_u8(buf: bytes, off: int) -> tuple[int, int]:
    return buf[off], off + 1


def _read_u16le(buf: bytes, off: int) -> tuple[int, int]:
    return int.from_bytes(buf[off:off + 2], "little"), off + 2


def _contract_columns() -> list[str]:
    cols: list[str] = []
    for item in CONTRACT:
        if item.get("repeat"):
            n = int(item["repeat"])
            prefix = str(item["column_prefix"])
            for idx in range(1, n + 1):
                for part in item["structure"]:
                    suffix = str(part["column_suffix"])
                    cols.append(f"{prefix}{idx:02d}{suffix}")
        else:
            if item.get("skip"):
                continue
            cols.extend(item["columns"])
    return cols


def _parse_one_block(block: bytes, encounterset_id: int, log_lines: list[str]) -> dict[str, int]:
    off = 0
    row: dict[str, int] = {"encounterset_id": encounterset_id}

    for item in CONTRACT:
        if item.get("repeat"):
            n = int(item["repeat"])
            prefix = str(item["column_prefix"])
            for idx in range(1, n + 1):
                for part in item["structure"]:
                    t = part["type"]
                    if t == "u8":
                        v, off = _read_u8(block, off)
                    elif t == "u16le":
                        v, off = _read_u16le(block, off)
                    else:
                        raise ValueError(f"Unsupported type in contract: {t}")
                    col = f"{prefix}{idx:02d}{part['column_suffix']}"
                    row[col] = v
            continue

        t = item["type"]
        cnt = int(item["count"])
        if item.get("skip"):
            # Optional validation that skipped bytes are 0x00
            if item.get("validate_zero"):
                skipped = block[off:off + cnt]
                if any(b != 0 for b in skipped):
                    log_lines.append(
                        f"[WARN] encounterset_id {encounterset_id}: expected padding zeros but found "
                        f"{skipped.hex(' ').upper()}"
                    )
            off += cnt
            continue

        cols = item["columns"]
        if len(cols) != cnt:
            raise ValueError(f"Contract mismatch for {item['name']}: count={cnt} but columns={len(cols)}")

        for col in cols:
            if t == "u8":
                v, off = _read_u8(block, off)
            elif t == "u16le":
                v, off = _read_u16le(block, off)
            else:
                raise ValueError(f"Unsupported type in contract: {t}")
            row[col] = v

    if off != BLOCK_SIZE:
        log_lines.append(f"[WARN] encounterset_id {encounterset_id}: parsed {off} bytes, expected {BLOCK_SIZE}.")
    return row


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _default_output_dir() -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return Path("output") / ts


def _write_log_if_needed(output_dir: Path, log_lines: list[str]) -> Path | None:
    if not log_lines:
        return None
    log_path = output_dir / LOG_FILENAME
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    return log_path


def _export_one_source(source_root: Path, lower_path: str, start_offset: int, output_csv: Path,
                       label: str, log_lines: list[str]) -> bool:
    src_path = source_root / Path(lower_path)
    if not src_path.exists():
        log_lines.append(f"[ERROR] Missing source for {label}: {src_path}")
        return False

    data = src_path.read_bytes()
    if start_offset >= len(data):
        log_lines.append(f"[ERROR] Start offset 0x{start_offset:X} beyond EOF for {label}: {src_path}")
        return False

    body = data[start_offset:]
    if len(body) < BLOCK_SIZE:
        log_lines.append(f"[ERROR] Not enough data for even one block for {label}: {src_path}")
        return False

    remainder = len(body) % BLOCK_SIZE
    if remainder != 0:
        log_lines.append(
            f"[WARN] {label}: data length from offset not multiple of {BLOCK_SIZE} "
            f"(len={len(body)}, remainder={remainder}). Trailing bytes will be ignored."
        )

    total_blocks = len(body) // BLOCK_SIZE
    headers = ["encounterset_id"] + _contract_columns()

    _ensure_dir(output_csv.parent)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for enc_id in range(total_blocks):
            start = enc_id * BLOCK_SIZE
            block = body[start:start + BLOCK_SIZE]
            row = _parse_one_block(block, enc_id, log_lines)
            w.writerow(row)

    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Export encounter data for HG and SS.")
    ap.add_argument("--source", required=True, help="Path to the ROM contents folder.")
    ap.add_argument("--output", default=None, help="Output folder. If omitted, a timestamped folder is created.")
    args = ap.parse_args()

    source_root = Path(args.source)
    if not source_root.exists():
        print(f"[ERROR] Source folder not found: {source_root}")
        return 1

    output_dir = Path(args.output) if args.output else _default_output_dir()

    log_lines: list[str] = []

    out1 = output_dir / OUTPUT_1_FILENAME
    out2 = output_dir / OUTPUT_2_FILENAME

    ok1 = _export_one_source(source_root, SOURCE_1_FILENAME, START_OFFSET, out1, "HG", log_lines)
    ok2 = _export_one_source(source_root, SOURCE_2_FILENAME, START_OFFSET, out2, "SS", log_lines)

    log_path = _write_log_if_needed(output_dir, log_lines)
    if log_path:
        print(f"[WARN] See log: {log_path}")

    if not ok1 and not ok2:
        print("[ERROR] No outputs produced (both sources failed).")
        return 1

    # Print only what we produced
    if ok1:
        print(f"[OK] Export complete: {out1}")
    if ok2:
        print(f"[OK] Export complete: {out2}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
