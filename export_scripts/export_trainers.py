import csv
import argparse
from datetime import datetime
from pathlib import Path

# ======================================
# Configuration
# ======================================

SOURCE_1_FILENAME = "data/a/0/5/5"  # trainer properties data (packed NARC)
SOURCE_2_FILENAME = "data/a/0/5/6"  # trainer party data (packed NARC)

OUTPUT_FILENAME = "trainers.csv"
LOG_FILENAME = "log_trainers.txt"

# Legacy offsets (kept for context; not used by this NARC-based worker)
SOURCE_1_START_OFFSET = 0x1744
SOURCE_1_BLOCK_SIZE = 20
SOURCE_2_START_OFFSET = 0x1744

SKIP_FIRST = True  # skip trainer_id 0 in output (still validate/parse)

# ======================================
# Output Schema (authoritative)
# ======================================

FIELDNAMES = [
    "trainer_id",
    "party_flag_explicit_moves",
    "party_flag_enable_held_items",
    "trainer_class_id",
    "party_size",
    "trainer_item_id_1",
    "trainer_item_id_2",
    "trainer_item_id_3",
    "trainer_item_id_4",
    "ai_flag_00_basic",
    "ai_flag_01_evaluate_attack",
    "ai_flag_02_expert",
    "ai_flag_03_setup",
    "ai_flag_04_risky",
    "ai_flag_05_damage_priority",
    "ai_flag_06_baton_pass",
    "ai_flag_07_tag_strategy",
    "ai_flag_08_check_hp",
    "ai_flag_09_weather",
    "ai_flag_10_harassment",
    "battle_flag_doubles",
    "party_member_1_dv",
    "party_member_1_ability_slot",
    "party_member_1_gender",
    "party_member_1_level",
    "party_member_1_species_id",
    "party_member_1_held_item",
    "party_member_1_explicit_move_id_1",
    "party_member_1_explicit_move_id_2",
    "party_member_1_explicit_move_id_3",
    "party_member_1_explicit_move_id_4",
    "party_member_1_ball_seal",
    "party_member_2_dv",
    "party_member_2_ability_slot",
    "party_member_2_gender",
    "party_member_2_level",
    "party_member_2_species_id",
    "party_member_2_held_item",
    "party_member_2_explicit_move_id_1",
    "party_member_2_explicit_move_id_2",
    "party_member_2_explicit_move_id_3",
    "party_member_2_explicit_move_id_4",
    "party_member_2_ball_seal",
    "party_member_3_dv",
    "party_member_3_ability_slot",
    "party_member_3_gender",
    "party_member_3_level",
    "party_member_3_species_id",
    "party_member_3_held_item",
    "party_member_3_explicit_move_id_1",
    "party_member_3_explicit_move_id_2",
    "party_member_3_explicit_move_id_3",
    "party_member_3_explicit_move_id_4",
    "party_member_3_ball_seal",
    "party_member_4_dv",
    "party_member_4_ability_slot",
    "party_member_4_gender",
    "party_member_4_level",
    "party_member_4_species_id",
    "party_member_4_held_item",
    "party_member_4_explicit_move_id_1",
    "party_member_4_explicit_move_id_2",
    "party_member_4_explicit_move_id_3",
    "party_member_4_explicit_move_id_4",
    "party_member_4_ball_seal",
    "party_member_5_dv",
    "party_member_5_ability_slot",
    "party_member_5_gender",
    "party_member_5_level",
    "party_member_5_species_id",
    "party_member_5_held_item",
    "party_member_5_explicit_move_id_1",
    "party_member_5_explicit_move_id_2",
    "party_member_5_explicit_move_id_3",
    "party_member_5_explicit_move_id_4",
    "party_member_5_ball_seal",
    "party_member_6_dv",
    "party_member_6_ability_slot",
    "party_member_6_gender",
    "party_member_6_level",
    "party_member_6_species_id",
    "party_member_6_held_item",
    "party_member_6_explicit_move_id_1",
    "party_member_6_explicit_move_id_2",
    "party_member_6_explicit_move_id_3",
    "party_member_6_explicit_move_id_4",
    "party_member_6_ball_seal",
]


# ======================================
# NARC parsing (container only)
# ======================================

class NarcError(Exception):
    pass


def _u16le(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off+2], "little")


def _u32le(b: bytes, off: int) -> int:
    return int.from_bytes(b[off:off+4], "little")


def _hex(b: bytes) -> str:
    return b.hex(" ").upper()


def narc_extract_files(data: bytes) -> list[bytes]:
    """Extract member files from a DS NARC archive using FATB/FIMG."""
    if len(data) < 16 or data[0:4] != b"NARC":
        raise NarcError("Missing NARC magic")

    header_size = _u16le(data, 0x0C)
    block_count = _u16le(data, 0x0E)
    if header_size < 16 or header_size > len(data):
        raise NarcError("Invalid NARC header size")

    off = header_size
    fatb_off = None
    fatb_size = None
    fimg_off = None
    fimg_size = None

    for _ in range(block_count):
        if off + 8 > len(data):
            raise NarcError("Truncated block header")
        tag = data[off:off+4]
        size = _u32le(data, off+4)
        if size < 8 or off + size > len(data):
            raise NarcError("Invalid block size")
        if tag == b"BTAF":
            fatb_off, fatb_size = off, size
        elif tag == b"GMIF":
            fimg_off, fimg_size = off, size
        off += size

    if fatb_off is None or fimg_off is None:
        raise NarcError("Missing FATB or FIMG block")

    file_count = _u16le(data, fatb_off + 8)
    entries_off = fatb_off + 0x0C
    if entries_off + file_count * 8 > fatb_off + fatb_size:
        raise NarcError("FATB truncated")

    fimg_data_off = fimg_off + 8
    fimg_data_len = fimg_size - 8
    if fimg_data_off + fimg_data_len > len(data):
        raise NarcError("FIMG truncated")
    fimg_data = data[fimg_data_off:fimg_data_off + fimg_data_len]

    files: list[bytes] = []
    for idx in range(file_count):
        eoff = entries_off + idx * 8
        start = _u32le(data, eoff)
        end = _u32le(data, eoff + 4)
        if end < start or end > len(fimg_data):
            raise NarcError(f"Invalid FATB range for file {idx}: {start}-{end} (fimg_len={len(fimg_data)})")
        files.append(fimg_data[start:end])

    return files


# ======================================
# Trainer decoding (per agreed reference)
# ======================================

def _parse_properties(block20: bytes) -> dict[str, int]:
    if len(block20) != 20:
        raise ValueError("properties block not 20 bytes")

    return {
        "party_flags": block20[0],
        "trainer_class": block20[1],
        "unused": block20[2],
        "party_size": block20[3],
        "item1": int.from_bytes(block20[4:6], "little"),
        "item2": int.from_bytes(block20[6:8], "little"),
        "item3": int.from_bytes(block20[8:10], "little"),
        "item4": int.from_bytes(block20[10:12], "little"),
        "ai_flags": int.from_bytes(block20[12:16], "little"),
        "battle_flags": int.from_bytes(block20[16:20], "little"),
    }


def _decode_party_flags(party_flags: int) -> tuple[int, int]:
    return (1 if (party_flags & 0x01) else 0,
            1 if (party_flags & 0x02) else 0)


def _decode_ai_flag(ai_flags: int, bit: int) -> int:
    return 1 if (ai_flags >> bit) & 1 else 0


def _decode_double_battle(battle_flags: int) -> int:
    return 1 if (battle_flags & 0x00000002) else 0


def _attr_to_gender(attr: int) -> str:
    g = attr & 0x03
    if g == 0x01:
        return "explicit_male"
    if g == 0x02:
        return "explicit_female"
    return "auto"


def _attr_to_ability(attr: int) -> str:
    a = attr & 0x30
    if a == 0x10:
        return "explicit_1"
    if a == 0x20:
        return "explicit_2"
    return "auto"


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _parse_party_payload(payload: bytes, party_flags: int, party_size: int) -> list[dict]:
    # dv(u8), attr(u8), level(u16le), species(u16le), [held_item(u16le)?], [moves(4*u16le)?], ball_seal(u16le)
    moves_on = (party_flags & 0x01) != 0
    items_on = (party_flags & 0x02) != 0
    per_mon = 8 + (8 if moves_on else 0) + (2 if items_on else 0)

    expected_len = party_size * per_mon
    if len(payload) != expected_len:
        raise ValueError(f"payload size mismatch: expected {expected_len}, got {len(payload)}")

    mons: list[dict] = []
    off = 0
    for _ in range(party_size):
        dv = payload[off]
        attr = payload[off + 1]
        level = int.from_bytes(payload[off + 2:off + 4], "little")
        species = int.from_bytes(payload[off + 4:off + 6], "little")
        cursor = off + 6

        held_item = None
        if items_on:
            held_item = int.from_bytes(payload[cursor:cursor + 2], "little")
            cursor += 2

        moves: list[int] = []
        if moves_on:
            for __ in range(4):
                moves.append(int.from_bytes(payload[cursor:cursor + 2], "little"))
                cursor += 2

        ball_seal = int.from_bytes(payload[cursor:cursor + 2], "little")

        mons.append({
            "dv": dv,
            "attr": attr,
            "level": level,
            "species": species,
            "held_item": held_item,
            "moves": moves,
            "ball_seal": ball_seal,
        })

        off += per_mon

    return mons


def _classify_and_log_trailing(
    trainer_id: int,
    per_mon: int,
    expected_len: int,
    actual_len: int,
    aligned_len: int,
    party_blob: bytes,
    log_lines: list[str],
) -> None:
    extra_len = actual_len - expected_len
    if extra_len <= 0:
        return

    # Alignment-only case: expected_len % 4 == 2, actual_len == align4(expected_len) (=> extra_len == 2)
    if expected_len % 4 == 2 and actual_len == aligned_len and extra_len == 2:
        log_lines.append(
            f"[INFO] trainer_id {trainer_id}: alignment padding detected (ignored). "
            f"expected_len={expected_len} actual_len={actual_len}"
        )
        return

    # Phantom party members: trailing bytes are full extra records
    if per_mon > 0 and extra_len % per_mon == 0:
        inferred_extra = extra_len // per_mon
        preview = party_blob[expected_len: expected_len + min(per_mon, 16)]
        log_lines.append(
            f"[WARN] trainer_id {trainer_id}: phantom party member data detected (ignored). "
            f"expected_len={expected_len} actual_len={actual_len} inferred_extra_members={inferred_extra} "
            f"preview={_hex(preview)}"
        )
        return

    # Irregular tail
    tail = party_blob[expected_len: expected_len + min(16, extra_len)]
    log_lines.append(
        f"[WARN] trainer_id {trainer_id}: unexpected trailing bytes beyond alignment region (ignored). "
        f"expected_len={expected_len} actual_len={actual_len} extra_len={extra_len} preview={_hex(tail)}"
    )


def _inspect_alignment_region(
    trainer_id: int,
    expected_len: int,
    actual_len: int,
    aligned_len: int,
    party_blob: bytes,
    log_lines: list[str],
) -> None:
    if actual_len <= expected_len:
        return
    # bytes between expected_len and min(actual_len, aligned_len)
    pad = party_blob[expected_len:min(actual_len, aligned_len)]
    if not pad:
        return
    if all(b == 0x00 for b in pad):
        return
    if all(b == 0xFF for b in pad):
        log_lines.append(f"[INFO] trainer_id {trainer_id}: alignment-region bytes use 0xFF ({_hex(pad)}).")
        return
    log_lines.append(f"[WARN] trainer_id {trainer_id}: unexpected bytes in alignment region after payload: {_hex(pad)}")


# ======================================
# Worker scaffolding (matches repo style)
# ======================================

def _default_output_dir() -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return Path("output") / ts


def main() -> int:
    ap = argparse.ArgumentParser(description="Export trainer data from ROM contents.")
    ap.add_argument("--source", required=True, help="Path to ROM contents root folder.")
    ap.add_argument("--output", default=None, help="Output directory (default: ./output/<timestamp>)")
    args = ap.parse_args()

    source_root = Path(args.source)
    if not source_root.exists():
        print(f"[ERROR] Source folder not found: {source_root}")
        return 1

    output_dir = Path(args.output) if args.output else _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_csv = output_dir / OUTPUT_FILENAME
    log_path = output_dir / LOG_FILENAME

    warnings: list[str] = []  # kept for parity with other workers (unused for now)
    log_lines: list[str] = []

    def _write_log() -> None:
        if not (warnings or log_lines):
            return
        log_path.write_text("\n".join(log_lines + warnings) + "\n", encoding="utf-8")

    def _fail(msg: str) -> int:
        print(msg)
        log_lines.append(msg)
        _write_log()
        return 1

    src1 = source_root / SOURCE_1_FILENAME
    src2 = source_root / SOURCE_2_FILENAME
    if not src1.exists():
        return _fail(f"[ERROR] Source file not found: {src1}")
    if not src2.exists():
        return _fail(f"[ERROR] Source file not found: {src2}")

    data1 = src1.read_bytes()
    data2 = src2.read_bytes()

    try:
        prop_files = narc_extract_files(data1)
    except Exception as e:
        return _fail(f"[ERROR] Failed to parse properties NARC: {e}")

    try:
        party_files = narc_extract_files(data2)
    except Exception as e:
        return _fail(f"[ERROR] Failed to parse party NARC: {e}")

    if len(prop_files) != len(party_files):
        return _fail(
            "[ERROR] Properties/party file count mismatch.\n"
            f"  properties_file_count={len(prop_files)}\n"
            f"  party_file_count={len(party_files)}"
        )

    total_trainers = len(prop_files)

    for trainer_id, block in enumerate(prop_files):
        if len(block) != SOURCE_1_BLOCK_SIZE:
            return _fail(f"[ERROR] trainer_id {trainer_id}: properties file size {len(block)} != 20")

    with output_csv.open("w", newline="", encoding="utf-8") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=FIELDNAMES)
        w.writeheader()

        for trainer_id in range(total_trainers):
            prop = prop_files[trainer_id]
            props = _parse_properties(prop)

            party_flags = int(props["party_flags"])
            trainer_class = int(props["trainer_class"])
            unused = int(props["unused"])
            party_size = int(props["party_size"])

            if party_flags & ~0x03:
                return _fail(f"[ERROR] trainer_id {trainer_id}: unsupported party_flags 0x{party_flags:02X}")

            if unused != 0:
                log_lines.append(
                    f"[WARN] trainer_id {trainer_id}: expected unused byte 0x00 but found 0x{unused:02X}"
                )

            moves_on, items_on = _decode_party_flags(party_flags)
            per_mon = 8 + (8 if moves_on else 0) + (2 if items_on else 0)

            party_blob = party_files[trainer_id]
            expected_len = party_size * per_mon
            aligned_len = _align4(expected_len)

            # Trainer 0 special-case
            if trainer_id == 0:
                if party_size != 0:
                    return _fail(f"[ERROR] trainer_id 0: expected party_size=0 but found {party_size}")
                if party_blob != b"\x00" * 8:
                    return _fail(f"[ERROR] trainer_id 0: expected 8 bytes of zeros but found {_hex(party_blob)}")
                mons: list[dict] = []
            else:
                if party_size == 0:
                    return _fail(f"[ERROR] trainer_id {trainer_id}: party_size=0 is invalid")
                if not (1 <= party_size <= 6):
                    return _fail(f"[ERROR] trainer_id {trainer_id}: party_size {party_size} outside expected range 1..6")

                actual_len = len(party_blob)
                if actual_len < expected_len:
                    return _fail(
                        f"[ERROR] trainer_id {trainer_id}: party file too short.\n"
                        f"  party_flags=0x{party_flags:02X} moves={moves_on} items={items_on} party_size={party_size}\n"
                        f"  per_mon={per_mon} expected_len={expected_len} actual_len={actual_len}\n"
                        f"  properties_20_bytes={_hex(prop)}\n"
                        f"  party_bytes_preview={_hex(party_blob[:min(32, actual_len)])}"
                    )

                # Log trailing behavior per agreed policy
                _classify_and_log_trailing(
                    trainer_id=trainer_id,
                    per_mon=per_mon,
                    expected_len=expected_len,
                    actual_len=actual_len,
                    aligned_len=aligned_len,
                    party_blob=party_blob,
                    log_lines=log_lines,
                )
                _inspect_alignment_region(
                    trainer_id=trainer_id,
                    expected_len=expected_len,
                    actual_len=actual_len,
                    aligned_len=aligned_len,
                    party_blob=party_blob,
                    log_lines=log_lines,
                )

                payload = party_blob[:expected_len]

                try:
                    mons = _parse_party_payload(payload, party_flags, party_size)
                except Exception as e:
                    return _fail(f"[ERROR] trainer_id {trainer_id}: failed to parse party payload: {e}")

            if SKIP_FIRST and trainer_id == 0:
                continue

            ai_flags = int(props["ai_flags"])
            battle_flags = int(props["battle_flags"])

            row: dict[str, object] = {}
            row["trainer_id"] = trainer_id
            row["party_flag_explicit_moves"] = moves_on
            row["party_flag_enable_held_items"] = items_on
            row["trainer_class_id"] = trainer_class
            row["party_size"] = party_size
            row["trainer_item_id_1"] = props["item1"]
            row["trainer_item_id_2"] = props["item2"]
            row["trainer_item_id_3"] = props["item3"]
            row["trainer_item_id_4"] = props["item4"]

            row["ai_flag_00_basic"] = _decode_ai_flag(ai_flags, 0)
            row["ai_flag_01_evaluate_attack"] = _decode_ai_flag(ai_flags, 1)
            row["ai_flag_02_expert"] = _decode_ai_flag(ai_flags, 2)
            row["ai_flag_03_setup"] = _decode_ai_flag(ai_flags, 3)
            row["ai_flag_04_risky"] = _decode_ai_flag(ai_flags, 4)
            row["ai_flag_05_damage_priority"] = _decode_ai_flag(ai_flags, 5)
            row["ai_flag_06_baton_pass"] = _decode_ai_flag(ai_flags, 6)
            row["ai_flag_07_tag_strategy"] = _decode_ai_flag(ai_flags, 7)
            row["ai_flag_08_check_hp"] = _decode_ai_flag(ai_flags, 8)
            row["ai_flag_09_weather"] = _decode_ai_flag(ai_flags, 9)
            row["ai_flag_10_harassment"] = _decode_ai_flag(ai_flags, 10)

            row["battle_flag_doubles"] = _decode_double_battle(battle_flags)

            # Party members wide columns (1..6)
            for idx in range(1, 7):
                prefix = f"party_member_{idx}_"
                if idx <= len(mons):
                    m = mons[idx - 1]
                    row[prefix + "dv"] = m["dv"]
                    row[prefix + "ability_slot"] = _attr_to_ability(int(m["attr"]))
                    row[prefix + "gender"] = _attr_to_gender(int(m["attr"]))
                    row[prefix + "level"] = m["level"]
                    row[prefix + "species_id"] = m["species"]

                    if items_on:
                        row[prefix + "held_item"] = m["held_item"] if m["held_item"] is not None else ""
                    else:
                        row[prefix + "held_item"] = ""

                    if moves_on:
                        moves = list(m["moves"])
                        for mi in range(4):
                            row[prefix + f"explicit_move_id_{mi+1}"] = moves[mi] if mi < len(moves) else ""
                    else:
                        for mi in range(4):
                            row[prefix + f"explicit_move_id_{mi+1}"] = ""

                    row[prefix + "ball_seal"] = m["ball_seal"]
                else:
                    row[prefix + "dv"] = ""
                    row[prefix + "ability_slot"] = ""
                    row[prefix + "gender"] = ""
                    row[prefix + "level"] = ""
                    row[prefix + "species_id"] = ""
                    row[prefix + "held_item"] = ""
                    for mi in range(4):
                        row[prefix + f"explicit_move_id_{mi+1}"] = ""
                    row[prefix + "ball_seal"] = ""

            w.writerow(row)

    _write_log()
    if log_lines:
        has_warn = any(line.startswith("[WARN]") for line in log_lines)
        if has_warn:
            print(f"[WARN] See log: {log_path}")
        else:
            print(f"[INFO] See log: {log_path}")

    print(f"[OK] Export complete: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
