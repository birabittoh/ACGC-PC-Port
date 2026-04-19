#!/usr/bin/env python3
"""
Animal Crossing (GCN) — USA vs EUR message comparison tool.

Usage:
    python tools/compare_dumps.py text/GAFE01_00/message_dump.txt text/GAFP01_00/msg_Eng.txt [--output report.txt]

Reads both dump files, aligns entries by ID, then:
  1. Reports entries present in one file but missing from the other.
  2. Aligns control codes by text-run boundaries and maps EUR payloads → USA opcodes.
  3. Optionally emits a JSON mapping file for the C code generator.
  4. Produces a per-entry diff of plain text content.

Both files are expected to use the format:
    [[ENTRY <N> START]]
    ... content lines ...
    (blank line or next [[ENTRY ...]] starts next block)

EUR control codes use the format <<CMDxx [b0 b1 ...]>> where xx is the TOTAL
byte length of the sequence (including the 0x80 escape and the length byte
itself), NOT an opcode. The bracketed bytes are the payload after escape+length.
"""

import re
import sys
import json
import argparse
from collections import defaultdict, Counter
from pathlib import Path


# ---------------------------------------------------------------------------
# USA control-code table  (from msg_tool.py / m_font.h)
# Maps  opcode_index -> (name, total_size_bytes)
# ---------------------------------------------------------------------------

CONT_SIZES = [
    2, 2, 2, 3, 2, 5, 2, 2, 5, 5, 5, 5, 5, 2, 4, 4,  # 0x00–0x0F
    4, 4, 4, 6, 8, 10, 6, 8, 10, 2, 2, 2, 2, 2, 2, 2,  # 0x10–0x1F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,    # 0x20–0x2F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2,    # 0x30–0x3F
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 6, 3, 3, 3, 3,    # 0x40–0x4F
    2, 4, 4, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 6, 3,    # 0x50–0x5F
    3, 4, 3, 2, 2, 6, 2, 2, 3, 3, 3, 3, 2, 2, 2, 2,    # 0x60–0x6F
    2, 2, 4, 4, 12, 14,                                  # 0x70–0x75
]

COMMANDS = [
    "MSGEND", "MSGCONTINUE", "MSGCLEAR", "PAUSE", "BTN", "TEXTCOLOR",
    "ABLECANCEL", "UNABLECANCEL", "DEMOPLR", "DEMONPC0", "DEMONPC1",
    "DEMONPC2", "DEMONPCQST", "OPENCHOICE", "SETFORCEMSG", "SETNEXTMSG0",
    "SETNEXTMSG1", "SETNEXTMSG2", "SETNEXTMSG3", "SETNEXTMSGRND2",
    "SETNEXTMSGRND3", "SETNEXTMSGRND4", "SETSELSTR2", "SETSELSTR3",
    "SETSELSTR4", "FORCENEXT", "STR_PLAYERNAME", "STR_TALKNAME", "STR_TAIL",
    "STR_YEAR", "STR_MONTH", "STR_WEEK", "STR_DAY", "STR_HOUR", "STR_MIN",
    "STR_SEC", "STR_FREE0", "STR_FREE1", "STR_FREE2", "STR_FREE3", "STR_FREE4",
    "STR_FREE5", "STR_FREE6", "STR_FREE7", "STR_FREE8", "STR_FREE9",
    "STR_DETERMINATION", "STR_COUNTRYNAME", "STR_RNDNUM", "STR_ITEM0",
    "STR_ITEM1", "STR_ITEM2", "STR_ITEM3", "STR_ITEM4", "STR_FREE10",
    "STR_FREE11", "STR_FREE12", "STR_FREE13", "STR_FREE14", "STR_FREE15",
    "STR_FREE16", "STR_FREE17", "STR_FREE18", "STR_FREE19", "STR_MAIL",
    "LUCK_NEUTRAL", "LUCK_RELATIONSHIP", "LUCK_UNPOPULAR", "LUCK_BAD",
    "LUCK_MONEY", "LUCK_GOODS", "LUCK_6", "LUCK_7", "LUCK_8", "LUCK_9",
    "MSGCONTENTS_NORMAL", "MSGCONTENTS_ANGRY", "MSGCONTENTS_SAD",
    "MSGCONTENTS_FUN", "MSGCONTENTS_SLEEPY", "COLORCHARS", "SNDCUT",
    "LINEOFS", "LINETYPE", "CHARSCALE", "BTN2", "BGMMAKE", "BGMDELETE",
    "MSGTIMEEND", "SNDTRGSYS", "LINESCALE", "SNDNOPAGE", "VOICETRUE",
    "VOICEFALSE", "SELNOB", "GIVEOPEN", "GIVECLOSE", "MSGCONTENTS_GLOOMY",
    "SELNOBCLOSE", "SETNEXTMSGRNDSECTION", "AGBDUMMY0", "AGBDUMMY1",
    "AGBDUMMY2", "SPACE", "AGBDUMMY3", "AGBDUMMY4", "MALEFEMALECHK",
    "GENDERCHAR", "AGBDUMMY6", "AGBDUMMY7", "AGBDUMMY8", "AGBDUMMY9",
    "AGBDUMMY10", "STR_ISLANDNAME", "SETCURSORJUST", "CLRCUSRORJUST",
    "CUTARTICLE", "CAPTIALIZE", "STR_AMPM", "SETNEXTMSG4", "SETNEXTMSG5",
    "SETSELSTR5", "SETSELSTR6",
]

# Name → opcode index
CMD_NAME_TO_OP = {name: i for i, name in enumerate(COMMANDS)}


# ---------------------------------------------------------------------------
# Regex patterns for the two dump formats
# ---------------------------------------------------------------------------

# EUR: <<CMDxx>> or <<CMDxx [b0 b1 ...]>>  (xx = total byte length, not opcode)
EUR_CMD_RE = re.compile(r'<<CMD([0-9A-Fa-f]{2})(?:\s*\[([^\]]*)\])??>>')

# USA: <<TAGNAME>> or <<TAGNAME [b0 b1 ...]>>
USA_TAG_RE = re.compile(r'<<([A-Z][A-Z0-9_]*)(?:\s*\[([^\]]*)\])??>>')

ENTRY_START_RE = re.compile(r'^\[\[ENTRY\s+(\d+)\s+START\]\]')


# ---------------------------------------------------------------------------
# File parser
# ---------------------------------------------------------------------------

def parse_entries(path: str) -> dict[int, str]:
    """Parse a message dump into {entry_id: raw_text_block}."""
    entries: dict[int, str] = {}
    current_id: int | None = None
    current_lines: list[str] = []

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = ENTRY_START_RE.match(line)
            if m:
                if current_id is not None:
                    entries[current_id] = "".join(current_lines).strip()
                current_id = int(m.group(1))
                current_lines = []
            elif current_id is not None:
                current_lines.append(line)

    if current_id is not None:
        entries[current_id] = "".join(current_lines).strip()

    return entries


# ---------------------------------------------------------------------------
# Segment splitting
# Splits a decoded text entry into alternating text/cmd tuples.
# ---------------------------------------------------------------------------

def split_usa(text: str) -> list[tuple[str, str, str]]:
    """Split a USA entry into (kind, name, args_hex) segments."""
    segs = []
    pos = 0
    for m in USA_TAG_RE.finditer(text):
        if m.start() > pos:
            chunk = text[pos:m.start()].strip()
            if chunk:
                segs.append(("text", chunk, ""))
        segs.append(("cmd", m.group(1), (m.group(2) or "").strip()))
        pos = m.end()
    if pos < len(text):
        chunk = text[pos:].strip()
        if chunk:
            segs.append(("text", chunk, ""))
    return segs


def split_eur(text: str) -> list[tuple[str, str, str]]:
    """Split a EUR entry into (kind, cmd_len_hex, payload_hex) segments.

    cmd_len_hex is the CMD type byte (= total length, e.g. '05').
    payload_hex is the content inside the brackets (bytes after escape+length).
    """
    segs = []
    pos = 0
    for m in EUR_CMD_RE.finditer(text):
        if m.start() > pos:
            chunk = text[pos:m.start()].strip()
            if chunk:
                segs.append(("text", chunk, ""))
        segs.append(("cmd", m.group(1).upper(), (m.group(2) or "").strip()))
        pos = m.end()
    if pos < len(text):
        chunk = text[pos:].strip()
        if chunk:
            segs.append(("text", chunk, ""))
    return segs


def _cmd_groups(segs: list) -> list[list]:
    """Return list of cmd-sublists, one per gap between text runs.

    E.g. for [cmd, text, cmd, cmd, text, cmd] returns:
      [[cmd], [cmd, cmd], [cmd]]
    """
    groups: list[list] = []
    current: list = []
    for seg in segs:
        if seg[0] == "text":
            groups.append(current)
            current = []
        else:
            current.append(seg)
    groups.append(current)
    return groups


# ---------------------------------------------------------------------------
# Mapping collector  (text-run-aligned)
# ---------------------------------------------------------------------------

def collect_mappings(
    usa_entries: dict[int, str],
    eur_entries: dict[int, str],
) -> tuple[dict, int, int]:
    """Align by text-run boundaries and build EUR payload → USA code mapping.

    Returns:
        mappings: dict {eur_payload_hex: Counter({(usa_tag, usa_args): count})}
        skipped:  number of entries where text-run counts differed (unaligned)
        aligned:  number of entries successfully aligned
    """
    # eur_payload -> Counter of (usa_tag, usa_args) observed at same position
    mappings: dict[str, Counter] = defaultdict(Counter)
    skipped = 0
    aligned = 0

    common = sorted(set(usa_entries) & set(eur_entries))
    for eid in common:
        usa_segs = split_usa(usa_entries[eid])
        eur_segs = split_eur(eur_entries[eid])

        usa_texts = [s for s in usa_segs if s[0] == "text"]
        eur_texts = [s for s in eur_segs if s[0] == "text"]

        if len(usa_texts) != len(eur_texts):
            skipped += 1
            continue

        usa_grps = _cmd_groups(usa_segs)
        eur_grps = _cmd_groups(eur_segs)

        # The number of cmd-groups = number of text runs + 1 (before first,
        # between each, after last).  Both sides should have the same count.
        if len(usa_grps) != len(eur_grps):
            skipped += 1
            continue

        aligned += 1
        for usa_cmds, eur_cmds in zip(usa_grps, eur_grps):
            if len(usa_cmds) != len(eur_cmds):
                # Group size mismatch (e.g. EUR-only gender code): skip group
                continue
            for (_, usa_tag, usa_args), (_, _eur_len, eur_payload) in zip(usa_cmds, eur_cmds):
                mappings[eur_payload][(usa_tag, usa_args)] += 1

    return mappings, skipped, aligned


# ---------------------------------------------------------------------------
# Plain-text extractor  (strips all control codes)
# ---------------------------------------------------------------------------

def plain_text_usa(text: str) -> str:
    return USA_TAG_RE.sub("", text).strip()


def plain_text_eur(text: str) -> str:
    return EUR_CMD_RE.sub("", text).strip()


# ---------------------------------------------------------------------------
# Mapping JSON emitter
# ---------------------------------------------------------------------------

def build_mapping_json(
    mappings: dict[str, Counter],
) -> dict:
    """Convert the raw mapping Counter into a JSON-serialisable dict.

    Output format:
        {
          "<eur_payload_hex>": {
            "mappings": [
              {"usa_tag": "...", "usa_args": "...", "count": N},
              ...
            ],
            "ambiguous": true/false
          }
        }
    """
    out = {}
    for eur_payload, counter in sorted(mappings.items()):
        entries_list = [
            {"usa_tag": tag, "usa_args": args, "count": cnt}
            for (tag, args), cnt in counter.most_common()
        ]
        out[eur_payload] = {
            "mappings": entries_list,
            "ambiguous": len(entries_list) > 1,
        }
    return out


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def compare(
    usa_path: str,
    eur_path: str,
    output_path: str | None,
    mapping_path: str | None,
    max_diff_entries: int = 50,
) -> None:
    print(f"Parsing USA: {usa_path}")
    usa_entries = parse_entries(usa_path)
    print(f"  → {len(usa_entries):,} entries found")

    print(f"Parsing EUR: {eur_path}")
    eur_entries = parse_entries(eur_path)
    print(f"  → {len(eur_entries):,} entries found")

    usa_ids = set(usa_entries)
    eur_ids = set(eur_entries)
    only_usa = sorted(usa_ids - eur_ids)
    only_eur = sorted(eur_ids - usa_ids)
    common   = sorted(usa_ids & eur_ids)

    lines: list[str] = []
    w = lines.append

    w("=" * 72)
    w("ANIMAL CROSSING GCN — USA vs EUR MESSAGE COMPARISON REPORT")
    w("=" * 72)
    w("")

    # ---- 1. Entry coverage ------------------------------------------------
    w("## 1. ENTRY COVERAGE")
    w(f"  USA entries : {len(usa_ids):,}")
    w(f"  EUR entries : {len(eur_ids):,}")
    w(f"  Common      : {len(common):,}")
    w(f"  Only in USA : {len(only_usa):,}")
    w(f"  Only in EUR : {len(only_eur):,}")
    w("")

    if only_usa:
        w(f"  Entries present ONLY in USA ({len(only_usa)}):")
        w("  " + ", ".join(str(i) for i in only_usa[:200]))
        if len(only_usa) > 200:
            w(f"  ... and {len(only_usa)-200} more")
        w("")

    if only_eur:
        w(f"  Entries present ONLY in EUR ({len(only_eur)}):")
        w("  " + ", ".join(str(i) for i in only_eur[:200]))
        if len(only_eur) > 200:
            w(f"  ... and {len(only_eur)-200} more")
        w("")

    # ---- 2. Control-code mapping ------------------------------------------
    w("## 2. CONTROL CODE MAPPING  (EUR payload → USA opcode)")
    w("  (Aligned by text-run boundaries; EUR payload = bytes after 0x80 <len>)")
    w("")

    mappings, skipped, aligned = collect_mappings(usa_entries, eur_entries)

    one_to_one  = {k: v for k, v in mappings.items() if len(v) == 1}
    ambiguous   = {k: v for k, v in mappings.items() if len(v) > 1}

    w(f"  Entries aligned on text-run boundaries : {aligned:,}")
    w(f"  Entries skipped (text-run count mismatch) : {skipped:,}")
    w(f"  Unique EUR payloads observed : {len(mappings):,}")
    w(f"  Payloads with 1-to-1 USA mapping : {len(one_to_one):,}")
    w(f"  Payloads with ambiguous / multiple USA forms : {len(ambiguous):,}")
    w("")

    w("  ### 1-to-1 mappings  (EUR payload → USA tag + args)")
    w(f"  {'EUR payload':<40} {'USA tag':<25} {'USA args'}")
    w("  " + "-" * 80)
    for eur_payload in sorted(one_to_one):
        (usa_tag, usa_args), _ = one_to_one[eur_payload].most_common(1)[0]
        w(f"  {eur_payload:<40} {usa_tag:<25} {usa_args}")
    w("")

    if ambiguous:
        w("  ### Ambiguous / 1-to-N mappings  (possible structural differences)")
        for eur_payload in sorted(ambiguous):
            w(f"  EUR payload: [{eur_payload}]")
            for (usa_tag, usa_args), cnt in ambiguous[eur_payload].most_common():
                w(f"      → {usa_tag:<25} args=[{usa_args}]  (×{cnt})")
        w("")

    # Discover USA codes that appear in the USA dump but have no aligned EUR peer
    all_usa_tags_seen = set()
    for counter in mappings.values():
        for (tag, _), _ in counter.items():
            all_usa_tags_seen.add(tag)

    # USA codes with no EUR alignment (might be OK if they only appear in skipped entries)
    unmatched_usa = sorted(set(COMMANDS) - all_usa_tags_seen)
    if unmatched_usa:
        w("  ### USA codes with no aligned EUR peer (appear only in skipped entries or not in data):")
        for name in unmatched_usa:
            w(f"    {name}")
        w("")

    # ---- 3. EUR payloads seen in non-aligned entries ----------------------
    # (We can still collect single-side stats from all entries)
    all_eur_payloads: Counter = Counter()
    for raw in eur_entries.values():
        for m in EUR_CMD_RE.finditer(raw):
            payload = (m.group(2) or "").strip()
            all_eur_payloads[payload] += 1

    unmapped_eur = sorted(p for p in all_eur_payloads if p not in mappings)
    w("## 3. EUR PAYLOADS NOT YET MAPPED TO A USA CODE")
    if unmapped_eur:
        w(f"  {len(unmapped_eur)} payload(s) seen only in non-aligned entries or never co-located with a USA code:")
        for p in unmapped_eur[:50]:
            w(f"    [{p}]  (×{all_eur_payloads[p]})")
        if len(unmapped_eur) > 50:
            w(f"    ... and {len(unmapped_eur)-50} more")
    else:
        w("  None — all observed EUR payloads have a USA mapping.")
    w("")

    # ---- 4. Plain-text diff (entries where dialogue text changed) ---------
    w(f"## 4. TEXT DIFFERENCES  (entries where plain text changed, first {max_diff_entries})")
    w("  (Control codes stripped; only actual dialogue text compared)")
    w("")

    text_diff_count = 0
    for eid in common:
        usa_text = plain_text_usa(usa_entries[eid])
        eur_text = plain_text_eur(eur_entries[eid])

        if usa_text == eur_text:
            continue

        text_diff_count += 1
        if text_diff_count > max_diff_entries:
            continue

        w(f"  Entry {eid}:")
        w(f"    USA: {usa_text[:120]}")
        w(f"    EUR: {eur_text[:120]}")
        w("")

    w(f"  Entries with text changes : {text_diff_count:,}")
    w("")

    report = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(report, encoding="utf-8")
        print(f"\nReport written to: {output_path}")
    else:
        print(report)

    # ---- Mapping JSON -------------------------------------------------------
    if mapping_path:
        mapping_data = build_mapping_json(mappings)
        Path(mapping_path).write_text(
            json.dumps(mapping_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Mapping JSON written to: {mapping_path}")
        print(f"  {len(mapping_data):,} unique EUR payloads")
        ambig_count = sum(1 for v in mapping_data.values() if v["ambiguous"])
        print(f"  {ambig_count} ambiguous payloads")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Animal Crossing USA vs EUR message dumps."
    )
    parser.add_argument("usa_file",  help="Path to message_dump.txt  (USA)")
    parser.add_argument("eur_file",  help="Path to msg_Eng.txt  (EUR)")
    parser.add_argument(
        "--output", "-o",
        default="ac_comparison_report.txt",
        help="Write report here (default: ac_comparison_report.txt)",
    )
    parser.add_argument(
        "--emit-mapping",
        metavar="FILE",
        help="Write EUR-payload → USA-opcode mapping JSON to FILE",
    )
    parser.add_argument(
        "--max-diffs", type=int, default=50,
        help="Max number of differing text entries to show (default: 50)",
    )
    args = parser.parse_args()

    compare(args.usa_file, args.eur_file, args.output, args.emit_mapping, args.max_diffs)


if __name__ == "__main__":
    main()
