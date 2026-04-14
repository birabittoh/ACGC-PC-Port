#!/usr/bin/env python3
"""l10n_flow.py - Localization workflow for the Animal Crossing GCN PC port.

Commands
--------
extract          Unpack forest_2nd.arc and dump USA message text for editing.
repack           Encode edited text and repack into a localized forest_2nd arc.
from-eur         Build localized forest_2nd + forest_1st arcs from an EUR TGC file
                 (NPC dialogue AND select strings are auto-translated from EUR disc).
dump-select      Dump the USA player-choice strings to a text file (English template).
dump-select-eur  Auto-populate a select text file from an EUR forest_1st_script.arc.

Quick start — build a French translation from the EUR disc
----------------------------------------------------------
    # 1. Extract the EUR TGC for French
    dtk disc extract orig/GAFP01_00/files/tgc/forest_Frn_Final_PAL50.tgc \\
        orig/GAFP01_00/tgc_Frn/

    # 2a. (Optional) Dump English choice strings as a translation template
    python -m tools.l10n_flow dump-select \\
        --usa-1st-arc orig/GAFE01_00/files/forest_1st.arc \\
        --out         text/select_Frn.txt
    #     Edit text/select_Frn.txt, then pass it with --select-txt below.

    # 2b. Generate both translation arcs in one step
    python -m tools.l10n_flow from-eur \\
        --eur-arc     orig/GAFP01_00/tgc_Frn/files/forest_msg.arc \\
        --usa-arc     orig/GAFE01_00/files/forest_2nd.arc \\
        --usa-1st-arc orig/GAFE01_00/files/forest_1st.arc \\
        --lang        fr-FR \\
        --select-txt  text/select_Frn.txt   # omit to keep English choice strings

    # 3. Set  language = fr-FR  in settings.ini and launch the game.

Supported EUR language tags (matching TGC filenames)
-----------------------------------------------------
    Eng -> en-EU    Frn -> fr-FR    Gmn -> de-DE
    Itl -> it-IT    Spn -> es-ES
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

META_FILE_NAME = "l10n_meta.json"

# ── NPC name translation tables ───────────────────────────────────────────────
# Extracted from EUR forest_1st_script.arc → string.bin (verified against live data).
# Order matches USA string_data.bin entries 517-536:
#   Tom Nook, Redd, Katrina, Saharah, Wendell, Jingle, Gracie, Joan,
#   Pelly, Phyllis, Pete, Copper, Porter, Jack, Gyroid, K.K.,
#   Rover, Chip, Timmy, Tommy
_NPC_NAME_USA = [
    "Tom Nook", "Redd", "Katrina", "Saharah", "Wendell", "Jingle",
    "Gracie", "Joan", "Pelly", "Phyllis", "Pete", "Copper", "Porter",
    "Jack", "Gyroid", "K.K.", "Rover", "Chip", "Timmy", "Tommy",
]
_NPC_NAME_INDEX_START = 517  # first string_data.bin index holding a NPC name

_EUR_NPC_NAMES: dict[str, list[str]] = {
    "it-IT": [
        "Tom Nook", "Volpolo", "Vanda", "Sahara", "Van Trik", "Jingle",
        "Griffa", "Nella", "Pelly", "Polly", "Tino", "Birro", "Ciufciuf",
        "Fifonio", "Giroide", "K.K.", "Girolamo", "Castore", "Mirco", "Marco",
    ],
    "fr-FR": [
        "Tom Nook", "Rounard", "Astrid", "Sarah", "Morsicus", "Rodolphe",
        "Carla", "Porcella", "Op\u00e9lie", "Elisabec", "Antoine", "Maret",
        "Lazare", "Jacqu\u0027O", "Gyro\u00efde", "K\u00e9k\u00e9",
        "Charly", "Castor", "M\u00e9li", "M\u00e9lo",
    ],
    "de-DE": [
        "Tom Nook", "Reiner", "Smeralda", "Aziza", "Winci", "Chris",
        "Grazia", "Siegrid", "Pelly", "Peggy", "Peter", "Harry", "Flip",
        "Jakob", "Gyroid", "K.K.", "Olli", "Bartholo", "Nepp", "Schlepp",
    ],
    "es-ES": [
        "Tom Nook", "Ladino", "Katrina", "Alcatifa", "Da Morsi", "Renato",
        "Graciela", "Juana", "Sol", "Estrella", "Carturo", "Vigilio",
        "Estasio", "Soponcio", "Giroide", "Totakeke", "Fran", "Mart\u00edn",
        "Tendo", "Nendo",
    ],
    # en-EU intentionally omitted: keep USA English names as-is
}
TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent

# ── Item / furniture name extraction from EUR forestd.rel.szs ─────────────────
# Offsets and sizes from pc_assets.c (4th column = ROM offset within foresta.rel.szs).
# Each entry: (output filename, USA foresta.rel.szs offset, byte size).
# Entries are 16-byte fixed-width strings, space-padded (mIN_ITEM_NAME_LEN = 16).
_ITEM_NAME_FILES: list[tuple[str, int, int]] = [
    ("itemName_paper.bin",      0x54F4A0, 0x1000),
    ("itemName_money.bin",      0x5504A0, 0x0040),
    ("itemName_tool.bin",       0x5504E0, 0x05C0),
    ("itemName_fish.bin",       0x550AA0, 0x0280),
    ("itemName_cloth.bin",      0x550D20, 0x0FF0),
    ("itemName_etc.bin",        0x551D10, 0x0310),
    ("itemName_carpet.bin",     0x552020, 0x0430),
    ("itemName_wall.bin",       0x552450, 0x0430),
    ("itemName_fruit.bin",      0x552880, 0x0080),
    ("itemName_plant.bin",      0x552900, 0x00B0),
    ("itemName_minidisk.bin",   0x5529B0, 0x0370),
    ("itemName_dummy.bin",      0x552D20, 0x0100),
    ("itemName_ticket.bin",     0x552E20, 0x0600),
    ("itemName_insect.bin",     0x553420, 0x02D0),
    ("itemName_hukubukuro.bin", 0x5536F0, 0x0020),
    ("itemName_kabu.bin",       0x553710, 0x0040),
    ("ftrName_table.bin",       0x553750, 0x4000),
    ("ftrName2_table.bin",      0x557750, 0x0F20),
]
# ftrName_table start offset in USA foresta.rel.szs (derived from pc_assets.c above).
_USA_FORESTA_FTR_OFFSET = 0x553750
# ftrName_table start offset in EUR forestd.rel.szs — identical for all 5 EUR
# language TGCs (Eng/Frn/Gmn/Itl/Spn), verified by inspection.
_EUR_FORESTD_FTR_OFFSET = 0x1E37D0


def _yaz0_decompress(data: bytes) -> bytes:
    """Decompress a Yaz0/SZS stream (Nintendo GameCube format)."""
    import struct
    if data[:4] != b'Yaz0':
        raise ValueError("Not a Yaz0 stream")
    dec_size = struct.unpack_from('>I', data, 4)[0]
    out = bytearray(dec_size)
    src, dst = 16, 0
    while dst < dec_size:
        if src >= len(data):
            break
        code = data[src]; src += 1
        for _ in range(8):
            if dst >= dec_size:
                break
            if code & 0x80:
                out[dst] = data[src]; src += 1; dst += 1
            else:
                b1 = data[src]; b2 = data[src + 1]; src += 2
                dist = ((b1 & 0x0F) << 8) | b2
                copy_src = dst - dist - 1
                n = (b1 >> 4) + 2
                if n == 2:
                    n = data[src] + 18; src += 1
                for _ in range(n):
                    out[dst] = out[copy_src]; copy_src += 1; dst += 1
            code <<= 1
    return bytes(out)


def _extract_item_names(eur_forestd_szs: Path, out_dir: Path, lang: str = "en-EU") -> int:
    """Extract translated item/furniture name bins from EUR forestd.rel.szs.

    Decompresses the SZS, then extracts 18 item/furniture name tables.

    Layout notes
    ------------
    ftrName_table is at offset 0x1E37D0 in ALL 5 EUR language TGCs (verified).

    For en-EU the section order before ftrName_table is identical to USA:
      paper(0x1000) money(0x40) tool(0x5C0) fish(0x280) cloth(0xFF0) ...

    For the four non-English languages (fr-FR, de-DE, it-IT, es-ES) the compiled
    REL places itemName_money at a different VMA; all other sections are still
    consecutive in the same order.  As a result the block from paper through kabu
    is 0x40 bytes shorter (0x4270 instead of 0x42B0), and money cannot be
    reliably located.  Those languages therefore skip money extraction (the game
    falls back to the built-in USA money strings at runtime).

    Writes each bin to out_dir/assets/<name>.bin.
    Returns the number of files written.
    """
    dec = _yaz0_decompress(eur_forestd_szs.read_bytes())

    # ftrName_table is always at the verified fixed offset for all 5 languages.
    eur_ftr_start = _EUR_FORESTD_FTR_OFFSET

    # For non-English languages the paper→kabu block is 0x40 bytes shorter
    # (no money section between paper and tool).
    is_non_eng = lang != "en-EU"
    # Size of the money section that is absent in non-English layout.
    _MONEY_SIZE = 0x0040

    out_assets = out_dir / "assets"
    out_assets.mkdir(parents=True, exist_ok=True)

    written = 0
    for filename, usa_off, size in _ITEM_NAME_FILES:
        rel = usa_off - _USA_FORESTA_FTR_OFFSET  # offset relative to ftrName_table in USA

        if filename == "itemName_money.bin" and is_non_eng:
            # money is at an unrelated VMA in non-English EUR; skip.
            continue

        if is_non_eng and usa_off > 0x5504A0:
            # In non-English EUR the money section (0x40 bytes) is absent from
            # this consecutive block, so every section after paper sits 0x40
            # bytes earlier than in the English/USA layout.
            eur_off = eur_ftr_start + rel - _MONEY_SIZE
        else:
            eur_off = eur_ftr_start + rel

        block = dec[eur_off: eur_off + size]
        if len(block) != size:
            print(f"  Warning: {filename}: expected {size:#x} bytes, got {len(block):#x} — skipping.")
            continue
        (out_assets / filename).write_bytes(block)
        written += 1

    return written


def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


# ── Helpers shared with bmg_to_msg ───────────────────────────────────────────

def _extract_arc(arc_path: str, out_dir: str) -> str:
    """Extract a JKR archive; return path to the extracted root directory."""
    sys.path.insert(0, str(TOOLS_DIR))
    from arc_tool import unpack_archive

    os.makedirs(out_dir, exist_ok=True)
    unpack_archive(arc_path, out_dir)
    # arc_tool creates a subdirectory named after the archive root
    entries = [e for e in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, e))]
    if not entries:
        raise RuntimeError(f"No directory found after extracting {arc_path} into {out_dir}")
    return os.path.join(out_dir, entries[0])


def _pack_arc(src_root: str, out_arc: str):
    sys.path.insert(0, str(TOOLS_DIR))
    from arc_tool import pack_archive

    os.makedirs(os.path.dirname(os.path.abspath(out_arc)), exist_ok=True)
    pack_archive(src_root, out_arc)


def _find_file(base: str, filename: str) -> str | None:
    for root, _, files in os.walk(base):
        if filename in files:
            return os.path.join(root, filename)
    return None


def parse_localized_archive_name(arc_path: Path):
    stem = arc_path.stem
    if "." not in stem:
        return stem, None
    base_name, language = stem.rsplit(".", 1)
    if not base_name or not language:
        return stem, None
    return base_name, language


# ── extract ───────────────────────────────────────────────────────────────────

def find_message_files(unpack_dir: Path):
    data_candidates = sorted(unpack_dir.rglob("message_data.bin"))
    if not data_candidates:
        raise FileNotFoundError(
            "Could not find message_data.bin in unpacked archive. "
            "For this PC port, message resources are in forest_2nd.arc."
        )
    for data_path in data_candidates:
        table_path = data_path.with_name("message_data_table.bin")
        if table_path.exists():
            return data_path, table_path
    raise FileNotFoundError("Found message_data.bin but message_data_table.bin was not found")


def get_archive_root(unpack_dir: Path, msg_data_path: Path) -> Path:
    rel = msg_data_path.relative_to(unpack_dir)
    if len(rel.parts) == 0:
        raise RuntimeError("Unexpected archive layout")
    return unpack_dir / rel.parts[0]


def extract_flow(args):
    arc_tool = TOOLS_DIR / "arc_tool.py"
    msg_tool = TOOLS_DIR / "msg_tool.py"

    source_arc = Path(args.arc).resolve()
    if not source_arc.exists():
        raise FileNotFoundError(f"Source archive not found: {source_arc}")

    work_dir = Path(args.workdir).resolve()
    unpack_dir = work_dir / "unpacked"
    text_out = Path(args.text).resolve() if args.text else work_dir / "message_dump.txt"
    meta_path = work_dir / META_FILE_NAME

    if unpack_dir.exists() and not args.force:
        raise FileExistsError(f"{unpack_dir} exists. Use --force to overwrite")
    if unpack_dir.exists() and args.force:
        shutil.rmtree(unpack_dir)

    work_dir.mkdir(parents=True, exist_ok=True)
    unpack_dir.mkdir(parents=True, exist_ok=True)

    run([sys.executable, str(arc_tool), str(source_arc), str(unpack_dir)])

    msg_data_path, msg_table_path = find_message_files(unpack_dir)
    archive_root = get_archive_root(unpack_dir, msg_data_path)

    run([sys.executable, str(msg_tool), "-m", "unpack", str(msg_data_path), str(text_out)])

    meta = {
        "source_arc": str(source_arc),
        "work_dir": str(work_dir),
        "unpack_dir": str(unpack_dir),
        "archive_root": str(archive_root),
        "message_data_path": str(msg_data_path),
        "message_table_path": str(msg_table_path),
        "text_dump_path": str(text_out),
        "message_data_size": msg_data_path.stat().st_size,
        "message_table_size": msg_table_path.stat().st_size,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Extracted: {source_arc}")
    print(f"Text dump: {text_out}")
    print(f"Metadata : {meta_path}")


# ── repack ────────────────────────────────────────────────────────────────────

def repack_flow(args):
    arc_tool = TOOLS_DIR / "arc_tool.py"
    msg_tool = TOOLS_DIR / "msg_tool.py"

    work_dir = Path(args.workdir).resolve()
    meta_path = work_dir / META_FILE_NAME

    if not meta_path.exists():
        raise FileNotFoundError(f"{meta_path} not found. Run the extract step first.")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    source_arc = Path(meta["source_arc"])
    archive_root = Path(meta["archive_root"])
    msg_data_path = Path(meta["message_data_path"])
    text_dump_path = Path(args.text).resolve() if args.text else Path(meta["text_dump_path"])

    if not text_dump_path.exists():
        raise FileNotFoundError(f"Text file not found: {text_dump_path}")
    if not archive_root.exists():
        raise FileNotFoundError(f"Unpacked archive root not found: {archive_root}")
    if not msg_data_path.exists():
        raise FileNotFoundError(f"message_data.bin not found: {msg_data_path}")

    run([
        sys.executable, str(msg_tool), "-m", "pack",
        str(text_dump_path), str(msg_data_path),
        "--data_size", hex(int(meta["message_data_size"])),
        "--table_size", hex(int(meta["message_table_size"])),
    ])

    if args.out:
        out_arc = Path(args.out).resolve()
    else:
        base_name, detected_language = parse_localized_archive_name(source_arc)
        language = args.language or detected_language
        if not language:
            raise ValueError(
                "Could not infer language. Use --language (e.g. pt-BR) or --out."
            )
        out_arc = ROOT_DIR / "translations" / language / f"{base_name}{source_arc.suffix}"

    out_arc.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(arc_tool), str(archive_root), str(out_arc)])
    print(f"Built localized archive: {out_arc}")

    if args.replace_source:
        backup = source_arc.with_suffix(source_arc.suffix + ".bak")
        shutil.copy2(source_arc, backup)
        shutil.copy2(out_arc, source_arc)
        print(f"Backed up original to  : {backup}")
        print(f"Replaced source archive: {source_arc}")


# ── from-eur helpers ──────────────────────────────────────────────────────────

def _build_forest_2nd(eur_arc_path: Path, usa_arc_path: Path, lang: str,
                      out_arc: Path, tmp: str) -> None:
    """Merge EUR text into USA message structure and pack forest_2nd.<lang>.arc."""
    from bmg_to_msg import convert_message_data

    # Extract EUR arc → find msg.bin
    print("\nExtracting EUR forest_msg.arc...")
    eur_root = _extract_arc(str(eur_arc_path), os.path.join(tmp, "eur"))
    eur_bin = _find_file(eur_root, "msg.bin")
    if not eur_bin:
        raise FileNotFoundError("msg.bin not found in EUR arc")

    # Extract USA arc → find message_data.bin / message_data_table.bin
    print("Extracting USA forest_2nd.arc...")
    usa_root = _extract_arc(str(usa_arc_path), os.path.join(tmp, "usa"))
    usa_data = _find_file(usa_root, "message_data.bin")
    usa_table = _find_file(usa_root, "message_data_table.bin")
    if not usa_data or not usa_table:
        raise FileNotFoundError(
            "message_data.bin or message_data_table.bin not found in USA arc"
        )

    # Merge EUR text into USA control-code structure
    print("Merging EUR text into USA control code structure...")
    with open(eur_bin, "rb") as f:
        eur_bmg = f.read()
    with open(usa_data, "rb") as f:
        usa_msg = f.read()
    with open(usa_table, "rb") as f:
        usa_tbl = f.read()

    new_data, new_table = convert_message_data(eur_bmg, usa_msg, usa_tbl)

    # Write merged data back into a copy of the USA unpacked tree, preserving
    # the archive root directory name ("bin2") so the repacked arc has the
    # correct layout.  A flat layout causes the game to crash (NULL deref).
    pack_arc_root = os.path.join(tmp, "pack2", os.path.basename(usa_root))
    shutil.copytree(usa_root, pack_arc_root)

    data_dst = _find_file(pack_arc_root, "message_data.bin")
    table_dst = _find_file(pack_arc_root, "message_data_table.bin")
    with open(data_dst, "wb") as f:
        f.write(new_data)
    with open(table_dst, "wb") as f:
        f.write(new_table)

    print(f"\nPacking forest_2nd.{lang}.arc...")
    _pack_arc(pack_arc_root, str(out_arc))
    print(f"  → {out_arc}")


def _translate_npc_names(pack_arc_root: str, lang: str) -> None:
    """Patch string_data.bin in pack_arc_root with translated NPC names for lang.

    Replaces entries _NPC_NAME_INDEX_START .. _NPC_NAME_INDEX_START+19 with the
    EUR localised names from _EUR_NPC_NAMES.  No-ops for en-EU (names unchanged).
    """
    if lang not in _EUR_NPC_NAMES:
        return  # en-EU or unknown — keep USA names

    sys.path.insert(0, str(TOOLS_DIR))
    from select_tool import parse_select, encode_ac_str, VALID_COUNT, TABLE_TOTAL
    import struct

    data_path  = _find_file(pack_arc_root, "string_data.bin")
    table_path = _find_file(pack_arc_root, "string_data_table.bin")
    if not data_path or not table_path:
        print("  Warning: string_data.bin not found — skipping NPC name translation.")
        return

    data_bytes  = Path(data_path).read_bytes()
    table_bytes = Path(table_path).read_bytes()
    orig_data_size  = len(data_bytes)
    orig_table_size = len(table_bytes)

    entries = list(parse_select(data_bytes, table_bytes))   # list[bytes], len=VALID_COUNT
    translated = _EUR_NPC_NAMES[lang]
    start = _NPC_NAME_INDEX_START

    for i, name in enumerate(translated):
        idx = start + i
        if idx >= VALID_COUNT:
            break
        encoded = encode_ac_str(name)
        entries[idx] = encoded

    # Re-encode into data + table
    new_data  = bytearray()
    new_table = bytearray(orig_table_size)  # TABLE_TOTAL * 4, zero-filled

    for i in range(VALID_COUNT):
        new_data.extend(entries[i])
        struct.pack_into(">I", new_table, i * 4, len(new_data))

    if len(new_data) < orig_data_size:
        new_data.extend(b"\x00" * (orig_data_size - len(new_data)))

    Path(data_path).write_bytes(bytes(new_data))
    Path(table_path).write_bytes(bytes(new_table))

    changed = sum(1 for i, n in enumerate(translated)
                  if n != _NPC_NAME_USA[i])
    print(f"  Translated {changed} NPC names for {lang}.")


def _extract_eur_select_strings(eur_1st_script_arc: Path, tmp: str) -> list[str]:
    """Extract player-choice strings from EUR forest_1st_script.arc → list[str].

    The EUR arc contains select.bin in BMG format with 607 entries that map
    1:1 to the USA select_data.bin entries.
    """
    from bmg_to_msg import parse_bmg
    from msg_tool import CHAR_MAP

    eur_root = _extract_arc(str(eur_1st_script_arc), os.path.join(tmp, "eur1s"))
    sel_bin = _find_file(eur_root, "select.bin")
    if not sel_bin:
        raise FileNotFoundError("select.bin not found in EUR forest_1st_script.arc")

    data = Path(sel_bin).read_bytes()
    offsets, dat1 = parse_bmg(data)

    strings: list[str] = []
    for i in range(len(offsets)):
        start = offsets[i]
        end = offsets[i + 1] if i + 1 < len(offsets) else len(dat1)
        raw = dat1[start:end]
        # Decode: plain AC charset bytes; skip EUR escape sequences (0x80)
        chars: list[str] = []
        j = 0
        while j < len(raw):
            b = raw[j]
            if b == 0x80:
                size = raw[j + 1] if j + 1 < len(raw) else 2
                j += max(size, 2)
            elif b == 0x00:
                break
            elif b < len(CHAR_MAP):
                chars.append(CHAR_MAP[b])
                j += 1
            else:
                j += 1
        strings.append("".join(chars))
    return strings


def dump_select_eur_flow(args):
    """Extract EUR select strings from forest_1st_script.arc → text file."""
    sys.path.insert(0, str(TOOLS_DIR))
    from select_tool import VALID_COUNT

    eur_1st_script = Path(args.eur_1st_script_arc).resolve()
    if not eur_1st_script.exists():
        raise FileNotFoundError(f"EUR forest_1st_script.arc not found: {eur_1st_script}")

    out_txt = Path(args.out).resolve()
    print(f"EUR 1st_script arc : {eur_1st_script}")
    print(f"Output text        : {out_txt}")

    with tempfile.TemporaryDirectory() as tmp:
        strings = _extract_eur_select_strings(eur_1st_script, tmp)

    # Write translation file
    lines = [
        "# Animal Crossing — select string translation file",
        f"# Auto-populated from EUR disc by tools/l10n_flow.py dump-select-eur",
        "#",
        "# Instructions:",
        "#   Translate the line after each [[ENTRY N]] marker.",
        "#   Leave the entry blank if you want the game to show spaces.",
        "#   Max display length is 16 characters (longer strings are clipped).",
        "#   Use the AC charset: standard ASCII plus accented chars",
        "#   (à é è ì ò ù â ê î ô û ä ë ï ö ü ñ ç ß Ä Ö Ü etc.).",
        "#   Do NOT modify the [[ENTRY N]] markers or comment lines.",
        "#   Control codes (<<...>>) are NOT supported in select strings.",
        "",
    ]
    for i in range(VALID_COUNT):
        lines.append(f"[[ENTRY {i}]]")
        if i < len(strings) and strings[i]:
            lines.append(strings[i])
        lines.append("")

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    non_empty = sum(1 for s in strings[:VALID_COUNT] if s)
    print(f"Dumped {non_empty} non-empty entries (of {VALID_COUNT}) → {out_txt}")


# EUR escape-code → USA escape-code mapping for forest_1st_script bins.
# EUR uses  0x80 0x05 0x04 0x00 <code>  (5-byte sequence).
# USA uses  0x7F <byte>               (2-byte sequence).
# Codes 0x10-0x1B map via +0x12; codes 0x1C-0x25 map via +0x1A.
# Codes 0x10 and 0x11 (article/category helpers) have no USA equivalent → skip.
_EUR_TO_USA_ESCAPE: dict[int, bytes] = {
    code: bytes([0x7F, code + 0x12]) for code in range(0x12, 0x1C)
}
_EUR_TO_USA_ESCAPE.update({
    code: bytes([0x7F, code + 0x1A]) for code in range(0x1C, 0x26)
})

# (BMG-name, USA data-file stem, USA table-slot count, USA padded data size)
_1ST_SCRIPT_BINS: list[tuple[str, str, int, int]] = [
    ("ps",     "ps",     1250, 0x4E20),
    ("psz",    "psz",    750,  0x1388),
    ("super",  "super",  1250, 0x4E20),
    ("superz", "superz", 750,  0x1388),
    ("mail",   "mail",   1500, 0x1FBD0),
    ("maila",  "maila",  750,  0x4E20),
    ("mailb",  "mailb",  750,  0x7530),
    ("mailc",  "mailc",  750,  0x2710),
]


def _eur_raw_to_usa_bytes(raw: bytes) -> bytes:
    """Translate one EUR BMG entry's raw bytes to USA _data.bin format.

    Replaces 5-byte EUR escape sequences (0x80 0x05 0x04 0x00 <code>) with
    their USA 2-byte equivalents (0x7F <byte>).  Stops at a NUL terminator.
    Bytes not part of an escape are passed through unchanged (they are already
    in the AC single-byte charset used by both EUR and USA).
    """
    out = bytearray()
    i = 0
    while i < len(raw):
        b = raw[i]
        if b == 0x80:
            size = raw[i + 1] if i + 1 < len(raw) else 2
            if size == 5 and i + 4 < len(raw) and raw[i + 2] == 0x04 and raw[i + 3] == 0x00:
                code = raw[i + 4]
                if code in _EUR_TO_USA_ESCAPE:
                    out.extend(_EUR_TO_USA_ESCAPE[code])
                # codes 0x10, 0x11 and anything else → silently dropped
            i += max(size, 2)
        elif b == 0x00:
            break
        else:
            out.append(b)
            i += 1
    return bytes(out)


def _translate_1st_script_bins(eur_1st_script_arc: Path, pack_arc_root: str,
                                tmp: str) -> None:
    """Replace USA letter/postscript bins with EUR-translated versions.

    Reads each BMG file from EUR forest_1st_script.arc, translates escape
    codes to USA format, and overwrites the corresponding _data.bin /
    _data_table.bin pair inside pack_arc_root.
    """
    from bmg_to_msg import parse_bmg
    import struct

    eur_root = _extract_arc(str(eur_1st_script_arc), os.path.join(tmp, "eur1s_bins"))
    # _extract_arc descends into the single top-level subdirectory, so eur_root
    # is already bin_1st_script/ — the bins live in its "data/" child.
    eur_data_dir = os.path.join(eur_root, "data")
    if not os.path.isdir(eur_data_dir):
        print("  Warning: bin_1st_script/data not found in EUR arc — skipping letter bin translation.")
        return

    for bmg_stem, usa_stem, table_slots, data_pad in _1ST_SCRIPT_BINS:
        bmg_path = os.path.join(eur_data_dir, f"{bmg_stem}.bin")
        if not os.path.exists(bmg_path):
            print(f"  Warning: {bmg_stem}.bin not found in EUR arc — skipping.")
            continue

        data_dst  = _find_file(pack_arc_root, f"{usa_stem}_data.bin")
        table_dst = _find_file(pack_arc_root, f"{usa_stem}_data_table.bin")
        if not data_dst or not table_dst:
            print(f"  Warning: {usa_stem}_data.bin not found in USA arc — skipping.")
            continue

        try:
            offsets, dat1 = parse_bmg(Path(bmg_path).read_bytes())
        except Exception as exc:
            print(f"  Warning: could not parse {bmg_stem}.bin ({exc}) — skipping.")
            continue

        # Build translated data + table
        data_out  = bytearray()
        table_out = bytearray(table_slots * 4)  # zero-filled

        n_translated = 0
        for i in range(min(len(offsets), table_slots)):
            start = offsets[i]
            end   = offsets[i + 1] if i + 1 < len(offsets) else len(dat1)
            raw   = dat1[start:end]
            translated = _eur_raw_to_usa_bytes(raw)
            if translated:
                n_translated += 1
            data_out.extend(translated)
            struct.pack_into(">I", table_out, i * 4, len(data_out))
        # Remaining slots beyond EUR entry count stay zero (empty)

        if len(data_out) < data_pad:
            data_out.extend(b"\x00" * (data_pad - len(data_out)))

        Path(data_dst).write_bytes(bytes(data_out))
        Path(table_dst).write_bytes(bytes(table_out))
        print(f"  Translated {n_translated} entries for {usa_stem}_data.bin")


def _build_forest_1st(usa_1st_arc: Path, lang: str, out_arc: Path,
                      tmp: str, select_txt: str | None,
                      eur_1st_script_arc: Path | None = None) -> None:
    """Pack forest_1st.<lang>.arc with translated (or English) select strings."""
    from select_tool import pack as sel_pack

    # Extract USA forest_1st.arc
    print("\nExtracting USA forest_1st.arc...")
    usa_root = _extract_arc(str(usa_1st_arc), os.path.join(tmp, "usa1"))

    usa_sel_data  = _find_file(usa_root, "select_data.bin")
    usa_sel_table = _find_file(usa_root, "select_data_table.bin")
    if not usa_sel_data or not usa_sel_table:
        raise FileNotFoundError(
            "select_data.bin or select_data_table.bin not found in USA forest_1st.arc"
        )

    pack_arc_root = os.path.join(tmp, "pack1", os.path.basename(usa_root))
    shutil.copytree(usa_root, pack_arc_root)

    # Translate NPC names in string_data.bin
    _translate_npc_names(pack_arc_root, lang)

    # Translate letter/postscript bins from EUR forest_1st_script.arc
    if eur_1st_script_arc and eur_1st_script_arc.exists():
        print("  Translating letter and postscript bins from EUR arc...")
        _translate_1st_script_bins(eur_1st_script_arc, pack_arc_root, tmp)

    # Determine the select text to use: explicit file > auto-extract from EUR > English fallback
    effective_select_txt = select_txt
    if not effective_select_txt and eur_1st_script_arc and eur_1st_script_arc.exists():
        print(f"  Auto-extracting select strings from EUR arc: {eur_1st_script_arc}")
        auto_txt = os.path.join(tmp, f"select_auto_{lang}.txt")
        strings = _extract_eur_select_strings(eur_1st_script_arc, tmp)
        from select_tool import VALID_COUNT
        lines = [
            "# Auto-populated from EUR disc",
            "",
        ]
        for i in range(VALID_COUNT):
            lines.append(f"[[ENTRY {i}]]")
            if i < len(strings) and strings[i]:
                lines.append(strings[i])
            lines.append("")
        Path(auto_txt).write_text("\n".join(lines), encoding="utf-8")
        effective_select_txt = auto_txt

    if effective_select_txt:
        print(f"  Using translated select strings: {effective_select_txt}")
        data_sz  = Path(usa_sel_data).stat().st_size
        table_sz = Path(usa_sel_table).stat().st_size
        data_dst  = _find_file(pack_arc_root, "select_data.bin")
        table_dst = _find_file(pack_arc_root, "select_data_table.bin")
        sel_pack(effective_select_txt, data_dst, table_dst, data_sz, table_sz)
    else:
        print("  No translated select strings provided — using English strings.")

    print(f"\nPacking forest_1st.{lang}.arc...")
    _pack_arc(pack_arc_root, str(out_arc))
    print(f"  → {out_arc}")


# ── from-eur ──────────────────────────────────────────────────────────────────

def from_eur_flow(args):
    """Build translation-ready forest_2nd + forest_1st arcs from a EUR TGC."""
    sys.path.insert(0, str(TOOLS_DIR))

    eur_arc   = Path(args.eur_arc).resolve()
    usa_2nd   = Path(args.usa_arc).resolve()
    usa_1st   = Path(args.usa_1st_arc).resolve() if args.usa_1st_arc else None
    lang      = args.lang
    select_txt = args.select_txt

    if not eur_arc.exists():
        raise FileNotFoundError(f"EUR arc not found: {eur_arc}")
    if not usa_2nd.exists():
        raise FileNotFoundError(f"USA forest_2nd arc not found: {usa_2nd}")
    if usa_1st and not usa_1st.exists():
        raise FileNotFoundError(f"USA forest_1st arc not found: {usa_1st}")

    # Resolve output paths
    if args.out:
        out_2nd = Path(args.out).resolve()
    else:
        base_name, _ = parse_localized_archive_name(usa_2nd)
        out_2nd = ROOT_DIR / "translations" / lang / f"{base_name}.{lang}{usa_2nd.suffix}"

    if usa_1st:
        base_1st, _ = parse_localized_archive_name(usa_1st)
        out_1st = ROOT_DIR / "translations" / lang / f"{base_1st}.{lang}{usa_1st.suffix}"
    else:
        out_1st = None

    print(f"EUR arc      : {eur_arc}")
    print(f"USA 2nd arc  : {usa_2nd}")
    if usa_1st:
        print(f"USA 1st arc  : {usa_1st}")
    if select_txt:
        print(f"Select text  : {select_txt}")
    print(f"Language     : {lang}")
    print(f"Output (2nd) : {out_2nd}")
    if out_1st:
        print(f"Output (1st) : {out_1st}")

    with tempfile.TemporaryDirectory() as tmp:
        _build_forest_2nd(eur_arc, usa_2nd, lang, out_2nd, tmp)

        if usa_1st and out_1st:
            # Auto-detect EUR forest_1st_script.arc alongside the EUR forest_msg.arc
            eur_1st_script = eur_arc.parent / "forest_1st_script.arc"
            _build_forest_1st(usa_1st, lang, out_1st, tmp, select_txt,
                               eur_1st_script if eur_1st_script.exists() else None)

    # Extract translated item/furniture names from EUR forestd.rel.szs
    eur_forestd = eur_arc.parent / "forestd.rel.szs"
    if eur_forestd.exists():
        print("\nExtracting translated item names from EUR forestd.rel.szs...")
        out_trans = ROOT_DIR / "translations" / lang
        n = _extract_item_names(eur_forestd, out_trans, lang)
        print(f"  → translations/{lang}/assets/  ({n} files)")
    else:
        print(f"\n  (forestd.rel.szs not found alongside forest_msg.arc — skipping item names)")

    print(f"\nDone! Drop the files into translations/{lang}/ and set")
    print(f"  language = {lang}")
    print(f"in settings.ini.")


# ── dump-select ───────────────────────────────────────────────────────────────

def dump_select_flow(args):
    """Dump USA player-choice strings from forest_1st.arc to a text file."""
    sys.path.insert(0, str(TOOLS_DIR))
    from select_tool import dump as sel_dump

    usa_1st = Path(args.usa_1st_arc).resolve()
    if not usa_1st.exists():
        raise FileNotFoundError(f"USA forest_1st.arc not found: {usa_1st}")

    out_txt = Path(args.out).resolve()

    print(f"USA 1st arc : {usa_1st}")
    print(f"Output text : {out_txt}")

    with tempfile.TemporaryDirectory() as tmp:
        usa_root = _extract_arc(str(usa_1st), os.path.join(tmp, "usa1"))
        sel_data  = _find_file(usa_root, "select_data.bin")
        sel_table = _find_file(usa_root, "select_data_table.bin")
        if not sel_data or not sel_table:
            raise FileNotFoundError(
                "select_data.bin or select_data_table.bin not found in forest_1st.arc"
            )
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        sel_dump(sel_data, sel_table, str(out_txt))

    print(f"\nTemplate written to {out_txt}")
    print("Translate each line after [[ENTRY N]], then pass the file to from-eur")
    print("  via --select-txt, or rebuild with:")
    print("  python -m tools.select_tool pack <text> <data.bin> <table.bin>")


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Localization workflow for the Animal Crossing GCN PC port.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # extract
    p = sub.add_parser("extract", help="Unpack archive and dump USA messages for editing")
    p.add_argument("--arc", required=True, help="Source archive (usually orig/GAFE01_00/files/forest_2nd.arc)")
    p.add_argument("--workdir", required=True, help="Working directory for unpacked archive + metadata")
    p.add_argument("--text", help="Output message text file (default: <workdir>/message_dump.txt)")
    p.add_argument("--force", action="store_true", help="Overwrite existing workdir")
    p.set_defaults(func=extract_flow)

    # repack
    p = sub.add_parser("repack", help="Encode edited messages and repack archive")
    p.add_argument("--workdir", required=True, help="Working directory created by extract")
    p.add_argument("--text", help="Edited message text file (default: the one created by extract)")
    p.add_argument("--out", help="Output arc path (default: translations/<lang>/forest_2nd.<lang>.arc)")
    p.add_argument("--language", help="Language tag for default output path (e.g. pt-BR)")
    p.add_argument("--replace-source", action="store_true", help="Backup and replace the original source arc")
    p.set_defaults(func=repack_flow)

    # from-eur
    p = sub.add_parser(
        "from-eur",
        help="Build localized arcs directly from an EUR TGC file (no manual translation)",
        description=(
            "Merges EUR text into the USA message structure and produces\n"
            "forest_2nd.<lang>.arc (NPC dialogue) and optionally\n"
            "forest_1st.<lang>.arc (player-choice strings).\n\n"
            "The USA control codes (NPC expressions, choice branching, item-name\n"
            "substitution) are preserved; only the text runs are replaced.\n\n"
            "EUR TGC files live in orig/GAFP01_00/tgc_<Lang>/files/forest_msg.arc\n"
            "after running:  dtk disc extract orig/GAFP01_00/game.ciso orig/GAFP01_00/\n"
            "                dtk disc extract <tgc_path> orig/GAFP01_00/tgc_<Lang>/\n\n"
            "Player-choice strings (forest_1st) are NOT stored in the EUR TGC;\n"
            "supply a translated text file via --select-txt (produced by\n"
            "  python -m tools.select_tool dump ... select_template.txt\n"
            "then translated by hand).\n"
            "Without --select-txt the English strings are used as a fallback."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--eur-arc", required=True,
                   help="EUR forest_msg.arc (e.g. orig/GAFP01_00/tgc_Frn/files/forest_msg.arc)")
    p.add_argument("--usa-arc", required=True,
                   help="USA forest_2nd.arc (orig/GAFE01_00/files/forest_2nd.arc)")
    p.add_argument("--usa-1st-arc",
                   help="USA forest_1st.arc (orig/GAFE01_00/files/forest_1st.arc); "
                        "required to also generate a translated forest_1st arc")
    p.add_argument("--select-txt",
                   help="Translated select-string text file for --usa-1st-arc "
                        "(produced by: python -m tools.select_tool dump ...); "
                        "omit to keep English choice strings")
    p.add_argument("--lang", required=True,
                   help="Language tag used for the output path (e.g. fr-FR, de-DE, it-IT, es-ES, en-EU)")
    p.add_argument("--out", help="Override output arc path for forest_2nd")
    p.set_defaults(func=from_eur_flow)

    # dump-select
    p = sub.add_parser(
        "dump-select",
        help="Dump USA player-choice strings to a text file for translation",
    )
    p.add_argument("--usa-1st-arc", required=True,
                   help="USA forest_1st.arc (orig/GAFE01_00/files/forest_1st.arc)")
    p.add_argument("--out", required=True,
                   help="Output text file (e.g. text/select_Itl.txt)")
    p.set_defaults(func=dump_select_flow)

    # dump-select-eur
    p = sub.add_parser(
        "dump-select-eur",
        help="Auto-populate a select-string text file from an EUR forest_1st_script.arc",
        description=(
            "Extracts the translated player-choice strings from the EUR disc's\n"
            "forest_1st_script.arc (select.bin in BMG format) and writes them\n"
            "into a ready-to-use translation text file — no manual translation needed.\n\n"
            "Example:\n"
            "  python -m tools.l10n_flow dump-select-eur \\\n"
            "      --eur-1st-script-arc orig/GAFP01_00/tgc_Itl/files/forest_1st_script.arc \\\n"
            "      --out text/select_Itl.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--eur-1st-script-arc", required=True,
                   help="EUR forest_1st_script.arc "
                        "(e.g. orig/GAFP01_00/tgc_Itl/files/forest_1st_script.arc)")
    p.add_argument("--out", required=True,
                   help="Output text file (e.g. text/select_Itl.txt)")
    p.set_defaults(func=dump_select_eur_flow)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
