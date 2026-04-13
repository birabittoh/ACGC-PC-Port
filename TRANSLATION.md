# Translation Guide

## Quick start — EUR languages

If you have both disc images, one script does everything:

```bash
# Default paths (orig/GAFE01_00/game.ciso and orig/GAFP01_00/game.ciso)
./extract_translations.sh

# Or provide paths explicitly
./extract_translations.sh path/to/USA.ciso path/to/EUR.ciso

# Also dump human-readable text files (useful as a reference for custom translators)
./extract_translations.sh --text

# Only dump text files, skip generating .arc archives
./extract_translations.sh --text-only
```

This extracts both discs, generates all five EUR language archives, and
prints the `settings.ini` snippet to activate them. Jump to
[Enable in settings](#step-5--enable-in-settings-1) when done.

The `--text` flag additionally writes `text/GAFP01_00/msg_<Lang>.txt` files
containing the full game script in a readable format — handy as source
material when working on a custom translation.

---

This guide also covers two manual workflows:

- **EUR languages** (EN, FR, DE, IT, ES) — generate directly from the PAL disc, no manual translation needed.
- **Custom translations** — export the USA text, edit it, and repack.

## Prerequisites

You need:
- The USA disc: `orig/GAFE01_00/game.ciso` (GAFE01)
- The EUR disc: `orig/GAFP01_00/game.ciso` (GAFP01) — EUR languages only
- `dtk` v1.6.2 — download it with:
  ```
  python3 tools/download_tool.py dtk build/tools/dtk --tag v1.6.2
  ```
  Then use `build/tools/dtk` in place of `dtk` below.

---

## EUR languages (FR, DE, IT, ES, EN-EU)

The PAL disc ships five localizations inside TGC container files. The
`from-eur` command extracts the text from one of them and merges it into
the USA message structure, producing a ready-to-use archive.

### Step 1 — Extract the USA disc

Only needed once:

```
dtk disc extract orig/GAFE01_00/game.ciso orig/GAFE01_00/
```

### Step 2 — Extract the EUR disc

Only needed once:

```
dtk disc extract orig/GAFP01_00/game.ciso orig/GAFP01_00/
```

### Step 3 — Extract the language TGC

Replace `Frn` with the language code you want (see table below):

```
dtk disc extract orig/GAFP01_00/files/tgc/forest_Frn_Final_PAL50.tgc \
    orig/GAFP01_00/tgc_Frn/
```

| TGC code | Language | Tag   |
|----------|----------|-------|
| `Eng`    | English (EUR) | `en-EU` |
| `Frn`    | French   | `fr-FR` |
| `Gmn`    | German   | `de-DE` |
| `Itl`    | Italian  | `it-IT` |
| `Spn`    | Spanish  | `es-ES` |

### Step 4 — Generate the translation archive

```
python3 -m tools.l10n_flow from-eur \
    --eur-arc orig/GAFP01_00/tgc_Frn/files/forest_msg.arc \
    --usa-arc orig/GAFE01_00/files/forest_2nd.arc \
    --lang fr-FR
```

This writes `translations/fr-FR/forest_2nd.fr-FR.arc`.

### Step 5 — Enable in settings

Open (or create) `settings.ini` next to the game executable and set:

```ini
[Localization]
language = fr-FR
```

The change takes effect on the next launch.

---

## Custom translations

Use this workflow to translate the game into any language not covered above,
or to correct/improve an existing translation.

### Step 1 — Extract the USA disc (if not done already)

```
dtk disc extract orig/GAFE01_00/game.ciso orig/GAFE01_00/
```

### Step 2 — Dump the message text

```
python3 -m tools.l10n_flow extract \
    --arc    orig/GAFE01_00/files/forest_2nd.arc \
    --workdir work/pt-BR
```

This creates `work/pt-BR/message_dump.txt` — the full game script in a
human-readable format with one entry per `[[ENTRY N START]]` block.

### Step 3 — Edit the text

Open `message_dump.txt` in any UTF-8 text editor and replace the English
lines. Keep all `<<COMMAND>>` tokens exactly as they are — they control
dialogue flow, NPC expressions, and item-name substitution.

### Step 4 — Repack

```
python3 -m tools.l10n_flow repack \
    --workdir work/pt-BR \
    --language pt-BR
```

This writes `translations/pt-BR/forest_2nd.pt-BR.arc`.

### Step 5 — Enable in settings

```ini
[Localization]
language = pt-BR
```

---

## Notes

- `translations/` and `work/` are ignored by git — generate them locally.
- To inspect the raw EUR text (useful as a translation reference), first
  unpack the arc with `arc_tool`, then run:
  ```
  python3 -m tools.arc_tool unpack \
      orig/GAFP01_00/tgc_Frn/files/forest_msg.arc /tmp/frn_msg/
  python3 -m tools.bmg_tool unpack \
      /tmp/frn_msg/bin_msg/data/msg.bin text_Frn.txt
  ```
  This requires the EUR disc and TGC to have been extracted (Steps 2–3 above).
