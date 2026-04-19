#!/usr/bin/env python3
"""
gen_pc_msg_eur_codes.py — Generate pc_msg_eur_codes.inc from pc_msg_eur_mapping.json.

Usage:
    python tools/gen_pc_msg_eur_codes.py [--mapping tools/pc_msg_eur_mapping.json]
                                          [--out pc/src/pc_msg_eur_codes.inc]

The generated file provides:
  static u32 pc_msg_eur_translate_cmd(const u8* eur_payload, u32 eur_len, u8* out);

which translates one EUR control-code payload (the bytes after 0x80 <total_size>)
into the equivalent USA bytes (starting with 0x7F <opcode>).
"""

import json
import argparse
import textwrap
from collections import defaultdict
from pathlib import Path

# Maps msg_tool COMMANDS names → mFont_CONT_CODE_* enum names
CMD_TO_ENUM = {
    "MSGEND":              "mFont_CONT_CODE_LAST",
    "MSGCONTINUE":         "mFont_CONT_CODE_CONTINUE",
    "MSGCLEAR":            "mFont_CONT_CODE_CLEAR",
    "PAUSE":               "mFont_CONT_CODE_CURSOR_SET_TIME",
    "BTN":                 "mFont_CONT_CODE_BUTTON",
    "TEXTCOLOR":           "mFont_CONT_CODE_COLOR",
    "ABLECANCEL":          "mFont_CONT_CODE_ABLE_CANCEL",
    "UNABLECANCEL":        "mFont_CONT_CODE_UNABLE_CANCEL",
    "DEMOPLR":             "mFont_CONT_CODE_SET_DEMO_ORDER_PLAYER",
    "DEMONPC0":            "mFont_CONT_CODE_SET_DEMO_ORDER_NPC0",
    "DEMONPC1":            "mFont_CONT_CODE_SET_DEMO_ORDER_NPC1",
    "DEMONPC2":            "mFont_CONT_CODE_SET_DEMO_ORDER_NPC2",
    "DEMONPCQST":          "mFont_CONT_CODE_SET_DEMO_ORDER_QUEST",
    "OPENCHOICE":          "mFont_CONT_CODE_SET_SELECT_WINDOW",
    "SETFORCEMSG":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_F",
    "SETNEXTMSG0":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_0",
    "SETNEXTMSG1":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_1",
    "SETNEXTMSG2":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_2",
    "SETNEXTMSG3":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_3",
    "SETNEXTMSGRND2":      "mFont_CONT_CODE_SET_NEXT_MESSAGE_RANDOM_2",
    "SETNEXTMSGRND3":      "mFont_CONT_CODE_SET_NEXT_MESSAGE_RANDOM_3",
    "SETNEXTMSGRND4":      "mFont_CONT_CODE_SET_NEXT_MESSAGE_RANDOM_4",
    "SETSELSTR2":          "mFont_CONT_CODE_SET_SELECT_STRING_2",
    "SETSELSTR3":          "mFont_CONT_CODE_SET_SELECT_STRING_3",
    "SETSELSTR4":          "mFont_CONT_CODE_SET_SELECT_STRING_4",
    "FORCENEXT":           "mFont_CONT_CODE_SET_FORCE_NEXT",
    "STR_PLAYERNAME":      "mFont_CONT_CODE_PUT_STRING_PLAYER_NAME",
    "STR_TALKNAME":        "mFont_CONT_CODE_PUT_STRING_TALK_NAME",
    "STR_TAIL":            "mFont_CONT_CODE_PUT_STRING_TAIL",
    "STR_YEAR":            "mFont_CONT_CODE_PUT_STRING_YEAR",
    "STR_MONTH":           "mFont_CONT_CODE_PUT_STRING_MONTH",
    "STR_WEEK":            "mFont_CONT_CODE_PUT_STRING_WEEK",
    "STR_DAY":             "mFont_CONT_CODE_PUT_STRING_DAY",
    "STR_HOUR":            "mFont_CONT_CODE_PUT_STRING_HOUR",
    "STR_MIN":             "mFont_CONT_CODE_PUT_STRING_MIN",
    "STR_SEC":             "mFont_CONT_CODE_PUT_STRING_SEC",
    "STR_FREE0":           "mFont_CONT_CODE_PUT_STRING_FREE0",
    "STR_FREE1":           "mFont_CONT_CODE_PUT_STRING_FREE1",
    "STR_FREE2":           "mFont_CONT_CODE_PUT_STRING_FREE2",
    "STR_FREE3":           "mFont_CONT_CODE_PUT_STRING_FREE3",
    "STR_FREE4":           "mFont_CONT_CODE_PUT_STRING_FREE4",
    "STR_FREE5":           "mFont_CONT_CODE_PUT_STRING_FREE5",
    "STR_FREE6":           "mFont_CONT_CODE_PUT_STRING_FREE6",
    "STR_FREE7":           "mFont_CONT_CODE_PUT_STRING_FREE7",
    "STR_FREE8":           "mFont_CONT_CODE_PUT_STRING_FREE8",
    "STR_FREE9":           "mFont_CONT_CODE_PUT_STRING_FREE9",
    "STR_DETERMINATION":   "mFont_CONT_CODE_PUT_STRING_DETERMINATION",
    "STR_COUNTRYNAME":     "mFont_CONT_CODE_PUT_STRING_COUNTRY_NAME",
    "STR_RNDNUM":          "mFont_CONT_CODE_PUT_STRING_RANDOM_NUMBER_2",
    "STR_ITEM0":           "mFont_CONT_CODE_PUT_STRING_ITEM0",
    "STR_ITEM1":           "mFont_CONT_CODE_PUT_STRING_ITEM1",
    "STR_ITEM2":           "mFont_CONT_CODE_PUT_STRING_ITEM2",
    "STR_ITEM3":           "mFont_CONT_CODE_PUT_STRING_ITEM3",
    "STR_ITEM4":           "mFont_CONT_CODE_PUT_STRING_ITEM4",
    "STR_FREE10":          "mFont_CONT_CODE_PUT_STRING_FREE10",
    "STR_FREE11":          "mFont_CONT_CODE_PUT_STRING_FREE11",
    "STR_FREE12":          "mFont_CONT_CODE_PUT_STRING_FREE12",
    "STR_FREE13":          "mFont_CONT_CODE_PUT_STRING_FREE13",
    "STR_FREE14":          "mFont_CONT_CODE_PUT_STRING_FREE14",
    "STR_FREE15":          "mFont_CONT_CODE_PUT_STRING_FREE15",
    "STR_FREE16":          "mFont_CONT_CODE_PUT_STRING_FREE16",
    "STR_FREE17":          "mFont_CONT_CODE_PUT_STRING_FREE17",
    "STR_FREE18":          "mFont_CONT_CODE_PUT_STRING_FREE18",
    "STR_FREE19":          "mFont_CONT_CODE_PUT_STRING_FREE19",
    "STR_MAIL":            "mFont_CONT_CODE_PUT_STRING_MAIL",
    "LUCK_NEUTRAL":        "mFont_CONT_CODE_SET_PLAYER_DESTINY0",
    "LUCK_RELATIONSHIP":   "mFont_CONT_CODE_SET_PLAYER_DESTINY1",
    "LUCK_UNPOPULAR":      "mFont_CONT_CODE_SET_PLAYER_DESTINY2",
    "LUCK_BAD":            "mFont_CONT_CODE_SET_PLAYER_DESTINY3",
    "LUCK_MONEY":          "mFont_CONT_CODE_SET_PLAYER_DESTINY4",
    "LUCK_GOODS":          "mFont_CONT_CODE_SET_PLAYER_DESTINY5",
    "LUCK_6":              "mFont_CONT_CODE_SET_PLAYER_DESTINY6",
    "LUCK_7":              "mFont_CONT_CODE_SET_PLAYER_DESTINY7",
    "LUCK_8":              "mFont_CONT_CODE_SET_PLAYER_DESTINY8",
    "LUCK_9":              "mFont_CONT_CODE_SET_PLAYER_DESTINY9",
    "MSGCONTENTS_NORMAL":  "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_NORMAL",
    "MSGCONTENTS_ANGRY":   "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_ANGRY",
    "MSGCONTENTS_SAD":     "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_SAD",
    "MSGCONTENTS_FUN":     "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_FUN",
    "MSGCONTENTS_SLEEPY":  "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_SLEEPY",
    "COLORCHARS":          "mFont_CONT_CODE_SET_COLOR_CHAR",
    "SNDCUT":              "mFont_CONT_CODE_SOUND_CUT",
    "LINEOFS":             "mFont_CONT_CODE_SET_LINE_OFFSET",
    "LINETYPE":            "mFont_CONT_CODE_SET_LINE_TYPE",
    "CHARSCALE":           "mFont_CONT_CODE_SET_CHAR_SCALE",
    "BTN2":                "mFont_CONT_CODE_BUTTON2",
    "BGMMAKE":             "mFont_CONT_CODE_BGM_MAKE",
    "BGMDELETE":           "mFont_CONT_CODE_BGM_DELETE",
    "MSGTIMEEND":          "mFont_CONT_CODE_MSG_TIME_END",
    "SNDTRGSYS":           "mFont_CONT_CODE_SOUND_TRG_SYS",
    "LINESCALE":           "mFont_CONT_CODE_SET_LINE_SCALE",
    "SNDNOPAGE":           "mFont_CONT_CODE_SOUND_NO_PAGE",
    "VOICETRUE":           "mFont_CONT_CODE_VOICE_TRUE",
    "VOICEFALSE":          "mFont_CONT_CODE_VOICE_FALSE",
    "SELNOB":              "mFont_CONT_CODE_SELECT_NO_B",
    "GIVEOPEN":            "mFont_CONT_CODE_GIVE_OPEN",
    "GIVECLOSE":           "mFont_CONT_CODE_GIVE_CLOSE",
    "MSGCONTENTS_GLOOMY":  "mFont_CONT_CODE_SET_MESSAGE_CONTENTS_GLOOMY",
    "SELNOBCLOSE":         "mFont_CONT_CODE_SELECT_NO_B_CLOSE",
    "SETNEXTMSGRNDSECTION":"mFont_CONT_CODE_SET_NEXT_MESSAGE_RANDOM_SECTION",
    "AGBDUMMY0":           "mFont_CONT_CODE_AGB_DUMMY0",
    "AGBDUMMY1":           "mFont_CONT_CODE_AGB_DUMMY1",
    "AGBDUMMY2":           "mFont_CONT_CODE_AGB_DUMMY2",
    "SPACE":               "mFont_CONT_CODE_SPACE",
    "AGBDUMMY3":           "mFont_CONT_CODE_AGB_DUMMY3",
    "AGBDUMMY4":           "mFont_CONT_CODE_AGB_DUMMY4",
    "MALEFEMALECHK":       "mFont_CONT_CODE_AGB_MALE_FEMALE_CHECK",
    "GENDERCHAR":          "mFont_CONT_CODE_GENDER_CHAR",
    "AGBDUMMY6":           "mFont_CONT_CODE_AGB_DUMMY6",
    "AGBDUMMY7":           "mFont_CONT_CODE_AGB_DUMMY7",
    "AGBDUMMY8":           "mFont_CONT_CODE_AGB_DUMMY8",
    "AGBDUMMY9":           "mFont_CONT_CODE_AGB_DUMMY9",
    "AGBDUMMY10":          "mFont_CONT_CODE_AGB_DUMMY10",
    "STR_ISLANDNAME":      "mFont_CONT_CODE_PUT_STRING_ISLAND_NAME",
    "SETCURSORJUST":       "mFont_CONT_CODE_SET_CURSOR_JUST",
    "CLRCUSRORJUST":       "mFont_CONT_CODE_CLR_CURSOR_JUST",
    "CUTARTICLE":          "mFont_CONT_CODE_CUT_ARTICLE",
    "CAPTIALIZE":          "mFont_CONT_CODE_CAPITAL_LETTER",
    "STR_AMPM":            "mFont_CONT_CODE_PUT_STRING_AM_PM",
    "SETNEXTMSG4":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_4",
    "SETNEXTMSG5":         "mFont_CONT_CODE_SET_NEXT_MESSAGE_5",
    "SETSELSTR5":          "mFont_CONT_CODE_SET_SELECT_STRING_5",
    "SETSELSTR6":          "mFont_CONT_CODE_SET_SELECT_STRING_6",
}

# USA opcodes whose arg bytes come directly from the last N bytes of the EUR
# payload (no remapping needed). Format: prefix_bytes → (usa_tag, prefix_len)
# These get a parametric "passthrough args" handler.
PARAMETRIC_PREFIXES = [
    # EUR prefix bytes (as hex string), usa_tag
    ("01 00 04",     "PAUSE"),        # EUR last byte = time arg
    ("01 00 09",     "LINEOFS"),      # EUR last byte = offset arg
    ("01 00 0A",     "SPACE"),        # EUR last byte = width arg
    ("01 00 0B",     "MSGTIMEEND"),   # EUR last byte = time arg
    ("01 00 05",     "LINESCALE"),    # EUR last byte = scale arg
    ("01 00 08",     "CHARSCALE"),    # EUR last byte = scale arg
    ("01 00 06",     "LINETYPE"),     # EUR last byte = type arg
    ("01 00 07",     "SNDCUT"),       # EUR last byte = flag arg
    ("01 00 0C",     "SNDTRGSYS"),    # EUR last byte = se_no arg
    ("0A 00 0D",     "SNDTRGSYS"),    # duplicate family for SNDTRGSYS
    ("0C 00 00",     "SETFORCEMSG"),  # EUR last 2 bytes = msg_no (u16 BE)
    ("0C 00 01",     "SETNEXTMSG0"),
    ("0C 00 02",     "SETNEXTMSG1"),
    ("0C 00 03",     "SETNEXTMSG2"),
    ("0C 00 04",     "SETNEXTMSG3"),
    ("0C 00 05",     "SETNEXTMSG4"),
    ("0C 00 06",     "SETNEXTMSG5"),
]


def hex_to_bytes(s: str) -> bytes:
    s = s.strip()
    return bytes(int(x, 16) for x in s.split()) if s else b""


def bytes_to_c_array(data: bytes) -> str:
    return ", ".join(f"0x{b:02X}" for b in data)


def generate(mapping_path: str, out_path: str) -> None:
    with open(mapping_path) as f:
        raw = json.load(f)

    # Build flat list: (eur_payload_bytes, usa_tag, usa_args_bytes)
    # Use most-common mapping for ambiguous entries.
    entries: list[tuple[bytes, str, bytes]] = []
    skipped_tags: set[str] = set()

    for eur_payload_hex, v in raw.items():
        best = v["mappings"][0]
        usa_tag = best["usa_tag"]
        usa_args_hex = best["usa_args"]

        if usa_tag not in CMD_TO_ENUM:
            skipped_tags.add(usa_tag)
            continue

        eur_bytes = hex_to_bytes(eur_payload_hex)
        usa_args = hex_to_bytes(usa_args_hex)

        # Skip entries that are likely alignment artifacts:
        # EUR payload is much longer than what the USA code expects.
        if usa_tag == "GENDERCHAR":
            continue  # handled separately by pc_msg_eur_translate_gender_cmd

        entries.append((eur_bytes, usa_tag, usa_args))

    if skipped_tags:
        print(f"  Skipped {len(skipped_tags)} unknown USA tags: {skipped_tags}")

    # Build the set of EUR payloads that are covered by parametric rules
    # so we can skip generating specific cases for those (the parametric
    # rule handles all values in the family, including unseen ones).
    parametric_covered: set[bytes] = set()
    parsed_parametric: list[tuple[bytes, str]] = []
    for prefix_hex, usa_tag in PARAMETRIC_PREFIXES:
        prefix = hex_to_bytes(prefix_hex)
        parsed_parametric.append((prefix, usa_tag))
        for eur_bytes, tag, _ in entries:
            if tag == usa_tag and eur_bytes[:len(prefix)] == prefix:
                parametric_covered.add(eur_bytes)

    # Sort: longer matches first (more specific wins in linear scan)
    entries.sort(key=lambda e: (-len(e[0]), e[0]))

    lines: list[str] = []
    w = lines.append

    w("/* AUTO-GENERATED by tools/gen_pc_msg_eur_codes.py — do not edit. */")
    w("/* Regenerate: python tools/gen_pc_msg_eur_codes.py              */")
    w("")
    w("/*")
    w(" * Translate one EUR control-code payload to USA bytes.")
    w(" * p:   EUR payload bytes (bytes after 0x80 <total_size>)")
    w(" * n:   number of payload bytes  (= total_size - 2)")
    w(" * out: output buffer (caller guarantees >= 16 bytes free)")
    w(" * Returns number of bytes written (>= 2), or 0 if unrecognised.")
    w(" *")
    w(" * The EUR gender-switch payload (first byte 0x13) is dispatched to")
    w(" * pc_msg_eur_translate_gender_cmd(), declared in pc_msg_eur.c.")
    w(" */")
    w("static u32 pc_msg_eur_translate_cmd(const u8* p, u32 n, u8* out)")
    w("{")
    w("    if (n == 0) return 0;")
    w("")

    # --- Parametric families (variable last byte(s) passed through as USA args) ---
    w("    /* --- Parametric command families ------------------------------------ */")
    for prefix_bytes, usa_tag in parsed_parametric:
        enum_name = CMD_TO_ENUM[usa_tag]
        opcode_idx = list(CMD_TO_ENUM.keys()).index(usa_tag)
        # Figure out how many trailing bytes are the "args"
        # Assumption: payload length = len(prefix) + n_args
        # The number of USA args = CONT_SIZES[opcode] - 2
        from tools.compare_dumps import CONT_SIZES, COMMANDS
        opcode = COMMANDS.index(usa_tag) if usa_tag in COMMANDS else -1
        if opcode < 0 or opcode >= len(CONT_SIZES):
            continue
        n_usa_args = CONT_SIZES[opcode] - 2
        n_prefix = len(prefix_bytes)
        total_eur = n_prefix + n_usa_args  # expected total EUR payload len

        cond_bytes = " && ".join(
            [f"n >= {total_eur}"] +
            [f"p[{i}] == 0x{b:02X}" for i, b in enumerate(prefix_bytes)]
        )
        w(f"    /* EUR: {' '.join(f'{b:02X}' for b in prefix_bytes)} <{n_usa_args}B> → {usa_tag} */")
        w(f"    if ({cond_bytes}) {{")
        w(f"        out[0] = 0x7F; out[1] = {enum_name};")
        for i in range(n_usa_args):
            w(f"        out[{2+i}] = p[{n_prefix+i}];")
        w(f"        return {2 + n_usa_args};")
        w("    }")

    w("")
    w("    /* --- Gender-switch (variable length) -------------------------------- */")
    w("    if (n >= 3 && p[0] == 0x13 && p[1] == 0x00 && p[2] == 0x14)")
    w("        return pc_msg_eur_translate_gender_cmd(p, n, out);")
    w("")

    # Determine max EUR payload length for fixed-width table (no compound literals)
    max_eur = max(
        (len(eur_bytes) for eur_bytes, usa_tag, _ in entries
         if eur_bytes not in parametric_covered),
        default=1
    )
    max_eur = max(max_eur, 1)

    w("    /* --- Exact-match lookup table --------------------------------------- */")
    w("    {")
    w(f"        static const struct {{ u8 ep[{max_eur}]; u8 en; u8 usa[16]; u8 un; }}")
    w("        kMap[] = {")

    emitted = 0
    for eur_bytes, usa_tag, usa_args in entries:
        if eur_bytes in parametric_covered:
            continue  # covered by parametric rule above
        enum_name = CMD_TO_ENUM[usa_tag]
        opcode = list(CMD_TO_ENUM.keys()).index(usa_tag)
        usa_full = bytes([0x7F, opcode]) + usa_args
        # Pad EUR bytes to max_eur with trailing zeros
        eur_padded = eur_bytes + bytes(max_eur - len(eur_bytes))
        eur_c = bytes_to_c_array(eur_padded)
        usa_c = bytes_to_c_array(usa_full)
        comment = f"/* {usa_tag} */"
        w(f"            {{ {{{eur_c}}}, {len(eur_bytes)},"
          f" {{{usa_c}}}, {len(usa_full)} }},  {comment}")
        emitted += 1

    w("        };")
    w(f"        static const int kMapLen = {emitted};")
    w("        int i;")
    w("        for (i = 0; i < kMapLen; i++) {")
    w("            if (n >= kMap[i].en && memcmp(p, kMap[i].ep, kMap[i].en) == 0) {")
    w("                memcpy(out, kMap[i].usa, kMap[i].un);")
    w("                return kMap[i].un;")
    w("            }")
    w("        }")
    w("    }")
    w("")
    w("    return 0; /* unrecognised EUR payload */")
    w("}")

    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Generated: {out_path}")
    print(f"  {emitted} exact-match entries")
    print(f"  {len(parsed_parametric)} parametric families")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate EUR→USA control-code translator from mapping JSON."
    )
    parser.add_argument("--mapping", default="tools/pc_msg_eur_mapping.json",
                        help="Input mapping JSON (from compare_dumps.py --emit-mapping)")
    parser.add_argument("--out", default="pc/src/pc_msg_eur_codes.inc",
                        help="Output .inc file")
    args = parser.parse_args()
    generate(args.mapping, args.out)


if __name__ == "__main__":
    main()
