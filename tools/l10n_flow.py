#!/usr/bin/env python3
"""l10n_flow.py - Localization workflow for the Animal Crossing GCN PC port.

Commands
--------
extract       Unpack forest_2nd.arc and dump USA message text for editing.
repack        Encode edited text and repack into a localized forest_2nd arc.
from-eur      Build a localized forest_2nd arc directly from an EUR TGC file
              (no manual translation needed for EN/FR/DE/ES/IT).

Quick start — build a French translation from the EUR disc
----------------------------------------------------------
    # 1. Extract the EUR TGC for French
    dtk disc extract orig/GAFP01_00/files/tgc/forest_Frn_Final_PAL50.tgc \\
        orig/GAFP01_00/tgc_Frn/

    # 2. Generate translations/fr-FR/forest_2nd.fr-FR.arc in one step
    python -m tools.l10n_flow from-eur \\
        --eur-arc  orig/GAFP01_00/tgc_Frn/files/forest_msg.arc \\
        --usa-arc  orig/GAFE01_00/files/forest_2nd.arc \\
        --lang     fr-FR

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
TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent


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


# ── from-eur ──────────────────────────────────────────────────────────────────

def from_eur_flow(args):
    """Build a translation-ready forest_2nd.<lang>.arc from a EUR TGC/BMG."""
    sys.path.insert(0, str(TOOLS_DIR))
    from bmg_to_msg import convert_message_data

    eur_arc = Path(args.eur_arc).resolve()
    usa_arc = Path(args.usa_arc).resolve()

    if not eur_arc.exists():
        raise FileNotFoundError(f"EUR arc not found: {eur_arc}")
    if not usa_arc.exists():
        raise FileNotFoundError(f"USA arc not found: {usa_arc}")

    lang = args.lang
    if args.out:
        out_arc = Path(args.out).resolve()
    else:
        base_name, _ = parse_localized_archive_name(usa_arc)
        out_arc = ROOT_DIR / "translations" / lang / f"{base_name}.{lang}{usa_arc.suffix}"

    print(f"EUR arc : {eur_arc}")
    print(f"USA arc : {usa_arc}")
    print(f"Language: {lang}")
    print(f"Output  : {out_arc}")

    with tempfile.TemporaryDirectory() as tmp:
        # Extract EUR arc → find msg.bin
        print("\nExtracting EUR arc...")
        eur_root = _extract_arc(str(eur_arc), os.path.join(tmp, "eur"))
        eur_bin = _find_file(eur_root, "msg.bin")
        if not eur_bin:
            raise FileNotFoundError("msg.bin not found in EUR arc")

        # Extract USA arc → find message_data.bin / message_data_table.bin
        print("Extracting USA arc...")
        usa_root = _extract_arc(str(usa_arc), os.path.join(tmp, "usa"))
        usa_data = _find_file(usa_root, "message_data.bin")
        usa_table = _find_file(usa_root, "message_data_table.bin")
        if not usa_data or not usa_table:
            raise FileNotFoundError("message_data.bin or message_data_table.bin not found in USA arc")

        # Merge
        print("Merging EUR text into USA control code structure...")
        with open(eur_bin, "rb") as f:
            eur_bmg = f.read()
        with open(usa_data, "rb") as f:
            usa_msg = f.read()
        with open(usa_table, "rb") as f:
            usa_tbl = f.read()

        new_data, new_table = convert_message_data(eur_bmg, usa_msg, usa_tbl)

        # Write merged data back into a copy of the USA unpacked tree
        pack_root = os.path.join(tmp, "pack")
        shutil.copytree(usa_root, pack_root)

        data_dst = _find_file(pack_root, "message_data.bin")
        table_dst = _find_file(pack_root, "message_data_table.bin")
        with open(data_dst, "wb") as f:
            f.write(new_data)
        with open(table_dst, "wb") as f:
            f.write(new_table)

        # Repack
        print("\nPacking arc...")
        inner_dirs = [d for d in os.listdir(pack_root) if os.path.isdir(os.path.join(pack_root, d))]
        if not inner_dirs:
            raise RuntimeError("Cannot find arc root in unpacked USA tree")
        _pack_arc(os.path.join(pack_root, inner_dirs[0]), str(out_arc))

    print(f"\nDone! Drop this file into translations/{lang}/ and set")
    print(f"  language = {lang}")
    print(f"in settings.ini.")


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
        help="Build a localized arc directly from an EUR TGC file (no manual translation)",
        description=(
            "Merges EUR text into the USA message structure.\n"
            "The USA control codes (NPC expressions, choice branching, item-name\n"
            "substitution) are preserved; only the text runs are replaced.\n\n"
            "EUR TGC files live in orig/GAFP01_00/tgc_<Lang>/files/forest_msg.arc\n"
            "after running:  dtk disc extract orig/GAFP01_00/game.ciso orig/GAFP01_00/\n"
            "                dtk disc extract <tgc_path> orig/GAFP01_00/tgc_<Lang>/"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--eur-arc", required=True,
                   help="EUR forest_msg.arc (e.g. orig/GAFP01_00/tgc_Frn/files/forest_msg.arc)")
    p.add_argument("--usa-arc", required=True,
                   help="USA forest_2nd.arc (orig/GAFE01_00/files/forest_2nd.arc)")
    p.add_argument("--lang", required=True,
                   help="Language tag used for the output path (e.g. fr-FR, de-DE, it-IT, es-ES, en-EU)")
    p.add_argument("--out", help="Override output arc path")
    p.set_defaults(func=from_eur_flow)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
