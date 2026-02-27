import os
import csv
import argparse
import re
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================
SOURCE_1_FILENAME = "expanded/textArchives/0222.txt"  # Item names
SOURCE_2_FILENAME = "expanded/textArchives/0237.txt"  # Species names
SOURCE_3_FILENAME = "expanded/textArchives/0720.txt"  # Ability names
SOURCE_4_FILENAME = "expanded/textArchives/0729.txt"  # Trainer names
SOURCE_5_FILENAME = "expanded/textArchives/0730.txt"  # Trainer class names
SOURCE_6_FILENAME = "expanded/textArchives/0735.txt"  # Type names
SOURCE_7_FILENAME = "expanded/textArchives/0749.txt"  # Move descriptions
SOURCE_8_FILENAME = "expanded/textArchives/0750.txt"  # Move names
SOURCE_9_FILENAME = "expanded/textArchives/0279.txt"  # Location names
SOURCE_10_FILENAME = "expanded/textArchives/0221.txt"  # Item descriptions
SOURCE_11_FILENAME = "expanded/textArchives/0803.txt"  # Species descriptions HG
SOURCE_12_FILENAME = "expanded/textArchives/0804.txt"  # Species descriptions SS

OUTPUT_1_FILENAME = "constants_item_names.csv"
OUTPUT_2_FILENAME = "constants_species_names.csv"
OUTPUT_3_FILENAME = "constants_ability_names.csv"
OUTPUT_4_FILENAME = "constants_trainer_names.csv"
OUTPUT_5_FILENAME = "constants_trainer_class_names.csv"
OUTPUT_6_FILENAME = "constants_type_names.csv"
OUTPUT_7_FILENAME = "constants_move_descriptions.csv"
OUTPUT_8_FILENAME = "constants_move_names.csv"
OUTPUT_9_FILENAME = "constants_location_names.csv"
OUTPUT_10_FILENAME = "constants_item_descriptions.csv"
OUTPUT_11_FILENAME = "constants_species_descriptions_hg.csv"
OUTPUT_12_FILENAME = "constants_species_descriptions_ss.csv"

LOG_FILENAME = "log_constants.txt"

SPECS = [
    (SOURCE_1_FILENAME, OUTPUT_1_FILENAME, "item_id", "item_name", "default"),
    (SOURCE_2_FILENAME, OUTPUT_2_FILENAME, "species_id", "species_name", "default"),
    (SOURCE_3_FILENAME, OUTPUT_3_FILENAME, "ability_id", "ability_name", "default"),
    (SOURCE_4_FILENAME, OUTPUT_4_FILENAME, "trainer_id", "trainer_name", "trainer_name"),
    (SOURCE_5_FILENAME, OUTPUT_5_FILENAME, "trainer_class_id", "trainer_class_name", "trainer_class"),
    (SOURCE_6_FILENAME, OUTPUT_6_FILENAME, "type_id", "type_name", "default"),
    (SOURCE_7_FILENAME, OUTPUT_7_FILENAME, "move_id", "move_description", "move_desc"),
    (SOURCE_8_FILENAME, OUTPUT_8_FILENAME, "move_id", "move_name", "default"),
    (SOURCE_9_FILENAME, OUTPUT_9_FILENAME, "location_id", "location_name", "default"),
    (SOURCE_10_FILENAME, OUTPUT_10_FILENAME, "item_id", "item_description", "desc2"),
    (SOURCE_11_FILENAME, OUTPUT_11_FILENAME, "species_id", "species_description", "desc2"),
    (SOURCE_12_FILENAME, OUTPUT_12_FILENAME, "species_id", "species_description", "desc2"),
]

TRAINER_NAME_RE = re.compile(r"^\{TRAINER_NAME:\s*(.*?)\}$")


# ======================================
# Helpers
# ======================================
def _read_lines_textarchive(path: Path, warnings: list[str]) -> tuple[list[str], str]:
    """
    Returns (lines, encoding_used).

    These archives are typically UTF-8. Decoding UTF-8 bytes as cp1252 produces
    mojibake like 'â€™' and 'Ã©'. Strategy:
      1) utf-8-sig strict
      2) utf-8 strict
      3) utf-8 with replacement (log a warning)
    """
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return data.decode(enc).splitlines(), enc
        except UnicodeDecodeError:
            continue

    warnings.append(f"[WARN] {path.name}: utf-8 strict decode failed; used utf-8 with replacement.")
    return data.decode("utf-8", errors="replace").splitlines(), "utf-8-replace"
def _transform(kind: str, s: str, warnings: list[str], context: str) -> str:
    if kind == "default":
        return s

    if kind == "trainer_name":
        m = TRAINER_NAME_RE.match(s)
        if not m:
            warnings.append(f"[INFO] {context}: trainer name did not match wrapper; kept raw value.")
            return s
        return m.group(1).strip()

    if kind == "trainer_class":
        return s.replace("[PK][MN]", "Pokémon")

    if kind == "move_desc":
        # Work on literal "\n" sequences (backslash + n).
        count = s.count(r"\n")

        # Logging rules:
        #  - INFO for 3 or 5 (observed vanilla variants)
        #  - WARN for anything outside exactly 4 but not 3/5
        #  - No log for exactly 4
        if count == 4:
            pass
        elif count in (3, 5):
            warnings.append(f"[INFO] {context}: expected 4 literal \\n sequences, found {count}.")
        else:
            warnings.append(f"[WARN] {context}: expected 4 literal \\n sequences, found {count}.")

        # Strip trailing literal "\n" sequences
        while s.endswith(r"\n"):
            s = s[:-2]

        # Replace remaining internal literal "\n" with spaces
        s = s.replace(r"\n", " ")
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s

    if kind == "desc2":
        # Work on literal "\n" sequences (backslash + n).
        count = s.count(r"\n")

        # Only WARN if 3 or more literal "\n" sequences.
        # No log for 0–2.
        if count >= 3:
            warnings.append(f"[WARN] {context}: unexpected literal \\n count {count}.")

        # Strip trailing literal "\n" sequences
        while s.endswith(r"\n"):
            s = s[:-2]

        # Replace remaining internal literal "\n" with spaces
        s = s.replace(r"\n", " ")
        s = re.sub(r"\s{2,}", " ", s).strip()
        return s


    warnings.append(f"[WARN] {context}: unknown transform kind '{kind}'; kept raw value.")
    return s


def _write_csv(path: Path, id_col: str, text_col: str, rows: list[tuple[int, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([id_col, text_col])
        for i, txt in rows:
            w.writerow([i, txt])


# ======================================
# Entry Point
# ======================================
def main() -> int:
    parser = argparse.ArgumentParser(description="Export textArchive constants into CSV lookup tables.")
    parser.add_argument("--source", required=True, help="Path to ROM contents directory")
    parser.add_argument("--output", default=None, help="Output directory (default: ./output/<timestamp>/)")
    args = parser.parse_args()

    # Determine output folder (timestamped if not provided)
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_dir = Path("output") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    source_root = Path(args.source)
    if not source_root.exists():
        print(f"[ERROR] Source folder not found: {source_root}")
        return 1

    warnings: list[str] = []
    outputs_written: list[Path] = []

    # Fail fast if any source files are missing
    missing = []
    for src_rel, _, _, _, _ in SPECS:
        p = source_root / src_rel
        if not p.exists():
            missing.append(str(p))
    if missing:
        for m in missing:
            warnings.append(f"[ERROR] Missing source file: {m}")
        log_path = output_dir / LOG_FILENAME
        log_path.write_text("\n".join(warnings) + "\n", encoding="utf-8")
        print(f"[ERROR] Missing {len(missing)} required textArchive file(s). See log: {log_path}")
        return 1

    # Export each file
    for src_rel, out_name, id_col, text_col, transform_kind in SPECS:
        src_path = source_root / src_rel
        out_path = output_dir / out_name

        try:
            lines, enc_used = _read_lines_textarchive(src_path, warnings)
        except UnicodeDecodeError:
            warnings.append(f"[ERROR] Could not decode source file: {src_path}")
            continue

        if len(lines) < 2:
            warnings.append(f"[ERROR] {src_path}: expected at least 2 lines (file header + one record).")
            continue

        records = lines[1:]  # ignore first row (file number)
        rows: list[tuple[int, str]] = []
        for idx, raw in enumerate(records):
            raw_line_number = idx + 2  # +1 for 0-index, +1 for skipped header
            ctx = f"{src_path.name}:record_index={idx},raw_line={raw_line_number}"
            rows.append((idx, _transform(transform_kind, raw, warnings, ctx)))

        _write_csv(out_path, id_col, text_col, rows)
        outputs_written.append(out_path)

    # Only create log if warnings/errors exist
    if warnings:
        log_path = output_dir / LOG_FILENAME
        log_path.write_text("\n".join(warnings) + "\n", encoding="utf-8")

        has_error = any(w.startswith("[ERROR]") for w in warnings)
        has_warn = any(w.startswith("[WARN]") for w in warnings)
        has_info = any(w.startswith("[INFO]") for w in warnings)

        if has_error:
            level = "ERROR"
        elif has_warn:
            level = "WARN"
        elif has_info:
            level = "INFO"
        else:
            level = "INFO"

        print(f"[{level}] {len(warnings)} note(s) written to {log_path}")
    if outputs_written:
        for p in outputs_written:
            print(f"[OK] Export complete: {p}")
        return 0

    print("[ERROR] No outputs produced.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
