# Animal Crossing Message Control Codes

This document provides a technical reference for the message control codes used in Animal Crossing, specifically focusing on the USA version and how they relate to the EUR translation format produced by `extract_translations.sh`.

## Format Overview

Control codes are special sequences embedded in text strings to control display logic, dynamic content, and audio.

### USA Version (`forest_2nd.arc`)
- **Prefix**: `0x7F`
- **Binary Format**: `0x7F [Type] [Parameters...]`
- **Text Dump Format**: Produced by `msg_tool.py` or `l10n_flow.py`: `<<MNEMONIC [XX XX ...]>>`
- **Parsing**: The `Type` byte is an index into `mFont_cont_info_tbl` which defines the fixed parameter length.

### EUR Version (BMG)
- **Prefix**: `0x80`
- **Binary Format**: `0x80 [Size] [Parameters...]`
- **Text Dump Format**: Produced by `bmg_tool.py` (via `extract_translations.sh --text`): `<<CMDXX [XX XX ...]>>`
- **Parsing**: The `Size` byte indicates the **total length** of the control sequence (including `0x80` and `Size`).

---

## How to Generate Text Dumps

### EUR Translations
To generate human-readable text files for all EUR languages:
```bash
./extract_translations.sh --text
```
This extracts the EUR disc and creates files like `text/GAFP01_00/msg_Frn.txt`. These use the `<<CMDXX>>` format.

### USA Original
To generate a human-readable text file for the USA version:
1. Ensure your USA disc image is at `orig/GAFE01_00/game.ciso`.
2. Run the extraction flow:
```bash
python -m tools.l10n_flow extract --arc orig/GAFE01_00/files/forest_2nd.arc --workdir ./workdir_usa
```
This produces `workdir_usa/message_dump.txt`. It uses the `<<MNEMONIC>>` format.

---

## Control Code Table (USA vs EUR)

| Hex | USA Mnemonic | EUR Mnemonic | USA Size | Description |
| :--- | :--- | :--- | :--- | :--- |
| `0x00` | `MSGEND` | `CMD05 [00 00 00]` | 2 | Terminates the current message string. |
| `0x01` | `MSGCONTINUE` | `CMD05 [01 00 00]` | 2 | Waits for input (A/B) then clears window and continues. |
| `0x02` | `MSGCLEAR` | `CMD05 [02 00 00]` | 2 | Clears window text and resets cursor. |
| `0x03` | `PAUSE` | `CMD06 [03 00 XX]` | 3 | Sets character typing delay (`u8 delay`). |
| `0x04` | `BTN` | `CMD05 [04 00 00]` | 2 | Pauses and waits for input (A/B) to proceed. |
| `0x05` | `TEXTCOLOR` | `CMD08 [05 00 R G B]` | 5 | Sets text color (`u8 r, g, b`). |
| `0x06` | `ABLECANCEL` | `CMD05 [06 00 00]` | 2 | Enables message skipping/fast-forward. |
| `0x07` | `UNABLECANCEL` | `CMD05 [07 00 00]` | 2 | Disables message skipping. |
| `0x08` | `DEMOPLR` | `CMD08 [08 00 ..]` | 5 | Sets player demo order (`u8 idx, u16 val`). |
| `0x0D` | `OPENCHOICE` | `CMD05 [0D 00 00]` | 2 | Opens the choice selection window. |
| `0x0E` | `SETFORCEMSG` | `CMD07 [01 00 04 00 0E]` | 4 | Sets next message ID (`u16 msg_no`). |
| `0x0F` | `SETNEXTMSG0` | `CMD07 [01 00 04 00 0F]` | 4 | Next message ID if choice 0 selected. |
| `0x10` | `SETNEXTMSG1` | `CMD07 [01 00 04 00 10]` | 4 | Next message ID if choice 1 selected. |
| `0x19` | `FORCENEXT` | `CMD05 [19 00 00]` | 2 | Automatically loads the next message. |
| `0x1A` | `STR_PLAYERNAME`| `CMD05 [1A 00 00]` | 2 | Inserts player name. |
| `0x1B` | `STR_TALKNAME` | `CMD05 [1B 00 00]` | 2 | Inserts talking NPC name. |
| `0x1C` | `STR_TAIL` | `CMD05 [1C 00 00]` | 2 | Inserts NPC catchphrase. |
| `0x24` | `STR_FREE0` | `CMD05 [24 00 00]` | 2 | Inserts dynamic "free" string 0. |
| `0x2F` | `STR_COUNTRYNAME`| `CMD05 [2F 00 00]` | 2 | Inserts town name (e.g. "Animalville"). |
| `0x31` | `STR_ITEM0` | `CMD05 [31 00 00]` | 2 | Inserts item name 0 (e.g. "red snapper"). |
| `0x4B` | `MSGCONTENTS_NORMAL`| `CMD05 [4B 00 00]` | 2 | Sets voice tone to normal. |
| `0x50` | `COLORCHARS` | `CMD09 [...]` | 6 | Color next `u8 count` chars (`u8 r, g, b`). |
| `0x67` | `SPACE` | `CMD06 [67 00 XX]` | 3 | Insert `u8 width` pixels of horizontal space. |
| `0x6A` | `MALEFEMALECHK` | `CMD09 [...]` | 6 | Branch dialogue by player gender. |
| `0x6B` | `GENDER_CHAR` | `CMD07 [...]` | 4 | Insert character based on player gender. |
| `0x74` | `CUTARTICLE` | `CMD05 [74 00 00]` | 2 | Next item name interpolation skips article (a/the). |
| `0x75` | `CAPTIALIZE` | `CMD05 [75 00 00]` | 2 | Next dynamic string starts with capital letter. |

*Note: In EUR BMG files, the core USA ID is typically the 3rd byte of the sequence. `CMD05` is the common wrapper for 2-byte USA codes.*

---

## Technical Details

### Timing and 60 FPS
- **`PAUSE` (0x03)**: The byte parameter is multiplied by 2.0. This accounts for the PC/GameCube port running at 60fps, whereas the original N64 version ran at 30fps.

### Article Suppression
- **`CUTARTICLE` (0x74)**: This code is crucial for Western localizations. It sets a temporary flag (`mMsg_STATUS_FLAG_CUT_ARTICLE`) which causes the next `STR_ITEM*` or `STR_FREE*` code to skip copying the indefinite/definite article from the string resource (e.g., "a red snapper" becomes "red snapper").

### Capitalization
- **`CAPTIALIZE` (0x75)**: Sets `mMsg_STATUS_FLAG_CAPITALIZE`. The next inserted dynamic string will have its first character passed through `mFont_small_to_capital`.
