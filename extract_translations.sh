#!/usr/bin/env bash
# extract_translations.sh — Extract all EUR language translations from disc images.
#
# Requires:
#   - Python 3
#   - The USA disc:  any .ciso/.iso/.gcm in orig/GAFE01_00/
#   - The EUR disc:  any .ciso/.iso/.gcm in orig/GAFP01_00/
#
# Usage:
#   ./extract_translations.sh [options] [USA.ciso [EUR.ciso]]
#
# Options:
#   --text, -t      Also dump human-readable text files for each language
#                   to text/GAFP01_00/msg_<Lang>.txt (useful for translators)
#   --text-only     Only dump text files, skip generating .arc archives
#
# Output (.arc):
#   translations/fr-FR/forest_2nd.fr-FR.arc
#   translations/de-DE/forest_2nd.de-DE.arc
#   translations/it-IT/forest_2nd.it-IT.arc
#   translations/es-ES/forest_2nd.es-ES.arc
#   translations/en-EU/forest_2nd.en-EU.arc
#
# Output (--text):
#   text/GAFP01_00/msg_Frn.txt  (French)
#   text/GAFP01_00/msg_Gmn.txt  (German)
#   ... etc.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colours ───────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
    C_BOLD='\033[1m'; C_GREEN='\033[32m'; C_YELLOW='\033[33m'
    C_RED='\033[31m'; C_RESET='\033[0m'
else
    C_BOLD=''; C_GREEN=''; C_YELLOW=''; C_RED=''; C_RESET=''
fi

info()  { echo -e "${C_GREEN}==>${C_RESET}${C_BOLD} $*${C_RESET}"; }
warn()  { echo -e "${C_YELLOW}warning:${C_RESET} $*"; }
die()   { echo -e "${C_RED}error:${C_RESET} $*" >&2; exit 1; }
step()  { echo -e "  ${C_BOLD}$*${C_RESET}"; }

# ── Parse flags ───────────────────────────────────────────────────────────────
DO_ARC=1
DO_TEXT=0
POSITIONAL=()

for arg in "$@"; do
    case "$arg" in
        --text|-t)   DO_TEXT=1 ;;
        --text-only) DO_TEXT=1; DO_ARC=0 ;;
        -*)          die "Unknown option: $arg" ;;
        *)           POSITIONAL+=("$arg") ;;
    esac
done

find_disc() {
    local dir="$1"
    for ext in ciso iso gcm; do
        local found
        found="$(find "$dir" -maxdepth 1 -name "*.${ext}" 2>/dev/null | head -1)"
        [ -n "$found" ] && echo "$found" && return
    done
}

USA_CISO="${POSITIONAL[0]:-$(find_disc orig/GAFE01_00)}"
EUR_CISO="${POSITIONAL[1]:-$(find_disc orig/GAFP01_00)}"

# ── Check Python ──────────────────────────────────────────────────────────────
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c "import sys; assert sys.version_info >= (3,9)" 2>/dev/null \
    || die "Python 3.9 or newer is required (found: $("$PYTHON" --version 2>&1))"

# ── Locate / download dtk ─────────────────────────────────────────────────────
DTK_TAG="v1.6.2"
DTK_CACHE="build/tools/dtk"

if [ -x "$DTK_CACHE" ]; then
    DTK="$DTK_CACHE"
else
    info "Downloading dtk $DTK_TAG..."
    mkdir -p "$(dirname "$DTK_CACHE")"
    "$PYTHON" tools/download_tool.py dtk "$DTK_CACHE" --tag "$DTK_TAG"
    DTK="$DTK_CACHE"
fi

"$DTK" --version > /dev/null || die "dtk not working at: $DTK"

# ── Validate disc images ──────────────────────────────────────────────────────
[ -n "$USA_CISO" ] && [ -f "$USA_CISO" ] || die "USA disc not found in orig/GAFE01_00/\n       Place a GAFE01 (USA) disc image (.ciso/.iso/.gcm) there, or pass it as the first argument."
[ -n "$EUR_CISO" ] && [ -f "$EUR_CISO" ] || die "EUR disc not found in orig/GAFP01_00/\n       Place a GAFP01 (EUR) disc image (.ciso/.iso/.gcm) there, or pass it as the second argument."

USA_ID=$("$DTK" disc info "$USA_CISO" 2>/dev/null | grep "Game ID" | grep -o 'GAFE[0-9][0-9]' || true)
EUR_ID=$("$DTK" disc info "$EUR_CISO" 2>/dev/null | grep "Game ID" | grep -o 'GAFP[0-9][0-9]' || true)

[ -n "$USA_ID" ] || die "$USA_CISO does not look like a USA Animal Crossing disc (expected GAFE01)"
[ -n "$EUR_ID" ] || die "$EUR_CISO does not look like a EUR Animal Crossing disc (expected GAFP01)"

USA_DIR="orig/GAFE01_00"
EUR_DIR="orig/GAFP01_00"

# ── Extract USA disc (needed for .arc output only) ────────────────────────────
USA_ARC="$USA_DIR/files/forest_2nd.arc"
USA_1ST_ARC="$USA_DIR/files/forest_1st.arc"
if [ "$DO_ARC" -eq 1 ]; then
    if [ -f "$USA_ARC" ]; then
        step "USA disc already extracted, skipping."
    else
        info "Extracting USA disc..."
        "$DTK" disc extract "$USA_CISO" "$USA_DIR/"
    fi
fi

# ── Extract EUR disc ──────────────────────────────────────────────────────────
EUR_TGC_DIR="$EUR_DIR/files/tgc"
if [ -d "$EUR_TGC_DIR" ]; then
    step "EUR disc already extracted, skipping."
else
    info "Extracting EUR disc..."
    "$DTK" disc extract "$EUR_CISO" "$EUR_DIR/"
fi

# ── Language table ────────────────────────────────────────────────────────────
# Format: "TGC_CODE:LANG_TAG"
LANGUAGES=(
    "Eng:en-EU"
    "Frn:fr-FR"
    "Gmn:de-DE"
    "Itl:it-IT"
    "Spn:es-ES"
)

# ── Process each language ─────────────────────────────────────────────────────
[ "$DO_ARC"  -eq 1 ] && info "Generating translation archives..."
[ "$DO_TEXT" -eq 1 ] && info "Dumping text files for translators..."
echo ""

TEXT_DIR="text/GAFP01_00"
ERRORS=()

for entry in "${LANGUAGES[@]}"; do
    TGC_CODE="${entry%%:*}"
    LANG_TAG="${entry##*:}"

    TGC_FILE="$EUR_TGC_DIR/forest_${TGC_CODE}_Final_PAL50.tgc"
    TGC_OUT="$EUR_DIR/tgc_${TGC_CODE}"
    EUR_ARC="$TGC_OUT/files/forest_msg.arc"

    # Extract TGC if needed (required for both arc and text)
    if [ ! -f "$EUR_ARC" ]; then
        step "[$LANG_TAG] Extracting TGC..."
        "$DTK" disc extract "$TGC_FILE" "$TGC_OUT/" > /dev/null
    fi

    # ── Copy msg.bin for runtime EUR loader ───────────────────────────────────
    RUNTIME_MSG="translations/$LANG_TAG/msg.bin"
    if [ ! -f "$RUNTIME_MSG" ]; then
        step "[$LANG_TAG] Extracting msg.bin for runtime..."
        TMP_MSG2=$(mktemp -d)
        trap 'rm -rf "$TMP_MSG2"' EXIT
        "$PYTHON" -c "
import sys; sys.path.insert(0,'.')
sys.path.insert(0,'./tools')
from arc_tool import unpack_archive
unpack_archive('$EUR_ARC', '$TMP_MSG2')
" 2>/dev/null
        MSG_BIN2=$(find "$TMP_MSG2" -name "msg.bin" | head -1)
        if [ -n "$MSG_BIN2" ]; then
            mkdir -p "translations/$LANG_TAG"
            cp "$MSG_BIN2" "$RUNTIME_MSG"
            echo -e "  ${C_GREEN}→ $RUNTIME_MSG${C_RESET}"
        else
            warn "[$LANG_TAG] msg.bin not found in forest_msg.arc"
        fi
        trap - EXIT
        rm -rf "$TMP_MSG2"
    fi

    # ── Text dump ─────────────────────────────────────────────────────────────
    if [ "$DO_TEXT" -eq 1 ]; then
        TEXT_OUT="$TEXT_DIR/msg_${TGC_CODE}.txt"
        if [ -f "$TEXT_OUT" ]; then
            step "[$LANG_TAG] text dump already exists, skipping."
        else
            step "[$LANG_TAG] Dumping text..."
            # Extract the msg arc into a temp dir, then run bmg_tool on msg.bin
            TMP_MSG=$(mktemp -d)
            trap 'rm -rf "$TMP_MSG"' EXIT
            "$PYTHON" -c "
import sys; sys.path.insert(0,'.')
sys.path.insert(0,'./tools')
from arc_tool import unpack_archive
unpack_archive('$EUR_ARC', '$TMP_MSG')
" 2>/dev/null
            MSG_BIN=$(find "$TMP_MSG" -name "msg.bin" | head -1)
            [ -n "$MSG_BIN" ] || { warn "[$LANG_TAG] msg.bin not found in arc"; ERRORS+=("$LANG_TAG(text)"); continue; }
            mkdir -p "$TEXT_DIR"
            "$PYTHON" -m tools.bmg_tool unpack "$MSG_BIN" "$TEXT_OUT"
            trap - EXIT
            rm -rf "$TMP_MSG"
            echo -e "  ${C_GREEN}→ $TEXT_OUT${C_RESET}"
        fi
    fi

    # ── Arc generation ────────────────────────────────────────────────────────
    if [ "$DO_ARC" -eq 1 ]; then
        OUT_ARC="translations/$LANG_TAG/forest_2nd.$LANG_TAG.arc"
        OUT_1ST_ARC="translations/$LANG_TAG/forest_1st.$LANG_TAG.arc"

        # Resolve optional translated select strings file
        SELECT_TXT="text/select_$TGC_CODE.txt"
        SELECT_OPT=""
        if [ -f "$SELECT_TXT" ]; then
            SELECT_OPT="--select-txt $SELECT_TXT"
        fi

        OUT_ASSETS_DIR="translations/$LANG_TAG/assets"
        if [ -f "$OUT_ARC" ] && [ -f "$OUT_1ST_ARC" ] && [ -d "$OUT_ASSETS_DIR" ]; then
            step "[$LANG_TAG] arcs and item names already exist, skipping."
        else
            step "[$LANG_TAG] Merging text into USA format..."
            L10N_OUT=$("$PYTHON" -m tools.l10n_flow from-eur \
                    --eur-arc     "$EUR_ARC" \
                    --usa-arc     "$USA_ARC" \
                    --usa-1st-arc "$USA_1ST_ARC" \
                    --lang        "$LANG_TAG" \
                    $SELECT_OPT 2>&1) && L10N_OK=1 || L10N_OK=0
            echo "$L10N_OUT" | grep -E "^  |→|Done|Extracting|assets|error|warn" || true
            if [ "$L10N_OK" -eq 1 ]; then
                echo -e "  ${C_GREEN}→ $OUT_ARC${C_RESET}"
                echo -e "  ${C_GREEN}→ $OUT_1ST_ARC${C_RESET}"
            else
                warn "[$LANG_TAG] arc generation failed."
                ERRORS+=("$LANG_TAG(arc)")
            fi
        fi
    fi

    echo ""
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
info "Done."

if [ "$DO_ARC" -eq 1 ]; then
    echo ""
    echo "Translation archives and item names:"
    for entry in "${LANGUAGES[@]}"; do
        LANG_TAG="${entry##*:}"
        for arc_name in "forest_2nd" "forest_1st"; do
            OUT_ARC="translations/$LANG_TAG/${arc_name}.${LANG_TAG}.arc"
            [ -f "$OUT_ARC" ] && echo "  $(du -h "$OUT_ARC" | cut -f1)  $OUT_ARC"
        done
        ASSETS_DIR="translations/$LANG_TAG/assets"
        if [ -d "$ASSETS_DIR" ]; then
            N=$(ls "$ASSETS_DIR"/*.bin 2>/dev/null | wc -l)
            echo "  ${N} files  $ASSETS_DIR/"
        fi
        MSG_RT="translations/$LANG_TAG/msg.bin"
        [ -f "$MSG_RT" ] && echo "  $(du -h "$MSG_RT" | cut -f1)  $MSG_RT  (runtime EUR messages)"
    done
    echo ""
    echo "To activate a language, add this to settings.ini:"
    echo "  [Localization]"
    echo "  language = fr-FR   # or de-DE / it-IT / es-ES / en-EU"
    echo ""
    echo "Player-choice strings (\"Never mind...\", \"Mail a letter\", etc.) and item/furniture"
    echo "names (\"detour sign\", \"tall cactus\", etc.) are auto-translated from the EUR disc"
    echo "— no manual work required."
    echo ""
    echo "To override with a custom translation for a specific language:"
    echo "  1. Dump the EUR strings as a starting point:"
    echo "       python -m tools.l10n_flow dump-select-eur \\"
    echo "           --eur-1st-script-arc orig/GAFP01_00/tgc_Itl/files/forest_1st_script.arc \\"
    echo "           --out text/select_Itl.txt   # Frn / Gmn / Spn / Eng"
    echo "  2. Edit text/select_<Lang>.txt"
    echo "  3. Delete translations/<lang>/forest_1st.<lang>.arc and re-run this"
    echo "     script — it picks up text/select_<Lang>.txt automatically."
fi

if [ "$DO_TEXT" -eq 1 ]; then
    echo ""
    echo "Text dumps (translator reference):"
    for entry in "${LANGUAGES[@]}"; do
        TGC_CODE="${entry%%:*}"
        LANG_TAG="${entry##*:}"
        TXT="$TEXT_DIR/msg_${TGC_CODE}.txt"
        [ -f "$TXT" ] && echo "  $(du -h "$TXT" | cut -f1)  $TXT  [$LANG_TAG]"
    done
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
    echo ""
    warn "The following steps failed: ${ERRORS[*]}"
    exit 1
fi
