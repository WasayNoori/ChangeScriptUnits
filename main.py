"""
ChangeScriptUnits
-----------------
Scans all .txt files in a target folder, converts imperial measurements
(inches / feet) to millimetres, and saves results to Output/.

Usage:
    python main.py                     # reads from ./Input
    python main.py "C:/path/to/folder" # reads from the given folder

Rounding rules:
    < 100 mm  → nearest 1 mm
    >= 100 mm → nearest 10 mm

Pre-processing:
    All double-quote characters (") are stripped from the file before any
    unit detection runs.

Unit detection (no " or ' used as unit indicators):
    Numeric  : 5 inches  5 IN  5 ft  5 feet  (decimal OK)
    Spelled  : five inches / twenty-three feet / twelve IN
               *** Any spelled-out number is logged; only converted when
                   followed by a recognised imperial unit. ***
    IN note  : lowercase "in" is skipped (too ambiguous); only "IN" (uppercase)
               is treated as an abbreviation when preceded by a digit.
"""

import re
import csv
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INCHES_TO_MM = 25.4
FEET_TO_MM   = 304.8

# ---------------------------------------------------------------------------
# Spelled-out number tables
# ---------------------------------------------------------------------------
ONES = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19,
}
TENS = {
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90,
}


def word_to_number(text):
    """
    Parse a simple or compound spelled-out integer.
    Supports: 'five', 'twenty', 'twenty-three', 'twenty three'.
    Returns an int or None if unrecognised.
    """
    t = text.lower().strip().replace('-', ' ')
    parts = t.split()
    if len(parts) == 1:
        w = parts[0]
        if w in ONES:
            return ONES[w]
        if w in TENS:
            return TENS[w]
        return None
    if len(parts) == 2:
        if parts[0] in TENS and parts[1] in ONES and 0 < ONES[parts[1]] < 10:
            return TENS[parts[0]] + ONES[parts[1]]
    return None


# ---------------------------------------------------------------------------
# Rounding / formatting
# ---------------------------------------------------------------------------
def round_mm(mm):
    if mm < 100:
        return round(mm)
    return round(mm / 10) * 10


def to_mm_str(mm_raw):
    return f"{round_mm(mm_raw)} mm"


# ---------------------------------------------------------------------------
# Build master regex
# ---------------------------------------------------------------------------
_ones_pat    = ('zero|one|two|three|four|five|six|seven|eight|nine|ten|'
                'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|'
                'eighteen|nineteen')
_tens_pat    = 'twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety'
_ones_nz_pat = 'one|two|three|four|five|six|seven|eight|nine'   # 1-9 only

# Spelled-out number: compound (tens + ones) tried first, then simple
_word_num = (
    r'(?i:'
    r'(?:' + _tens_pat + r')[-\s](?:' + _ones_nz_pat + r')'   # twenty-three / twenty three
    r'|(?:' + _tens_pat + r')'                                  # twenty
    r'|(?:' + _ones_pat + r')'                                  # five, twelve …
    r')'
)

# Imperial unit:
#   Long forms (inches, inch, feet, foot, ft) → case-insensitive
#   Abbreviation IN                            → UPPERCASE ONLY
_imp_unit = r'(?:(?i:inches|inch|feet|foot|ft)|IN)'

MASTER_PATTERN = re.compile(
    # ── 1. Numeric feet:  5 ft  5feet  5 FEET  ───────────────────────────────
    r'(\d+(?:\.\d+)?)\s*(?i:feet|foot|ft)(?![a-zA-Z])'
    r'|'
    # ── 2. Numeric inches:  5 inches  5 IN  (NOT 5 in) ───────────────────────
    r'(\d+(?:\.\d+)?)\s*(?:(?i:inches|inch)(?![a-zA-Z])|IN(?![a-zA-Z]))'
    r'|'
    # ── 3. Spelled-out WITH imperial unit  →  convert ────────────────────────
    r'(?<!\w)(' + _word_num + r')\s+(' + _imp_unit + r')(?![a-zA-Z])'
    r'|'
    # ── 4. Spelled-out WITHOUT imperial unit  →  log only, no change ─────────
    r'(?<!\w)(' + _word_num + r')(?!\s+' + _imp_unit + r'(?![a-zA-Z]))'
)
# Group index reference:
#   g1     → numeric feet
#   g2     → numeric inches
#   g3, g4 → spelled number + unit  (convert)
#   g5     → spelled number, no unit (log only)


# ---------------------------------------------------------------------------
# Replacement callback factory
# ---------------------------------------------------------------------------
def make_replacer(filename, log_entries):
    def replacer(m):
        original = m.group(0)
        g1      = m.group(1)
        g2      = m.group(2)
        g3, g4  = m.group(3), m.group(4)
        g5      = m.group(5)

        # ── Determine mm_raw ────────────────────────────────────────────────
        if g1 is not None:
            mm_raw = float(g1) * FEET_TO_MM

        elif g2 is not None:
            mm_raw = float(g2) * INCHES_TO_MM

        elif g3 is not None:
            num = word_to_number(g3)
            if num is None:
                return original                    # unrecognised word, skip
            unit = g4.lower()
            mm_raw = num * (FEET_TO_MM if unit in ('feet', 'foot', 'ft')
                            else INCHES_TO_MM)

        elif g5 is not None:
            # Spelled-out number with no unit → flag, leave text unchanged
            log_entries.append({
                'File Name'             : filename,
                'Dimension Found'       : original,
                'Raw Conversion result' : 'N/A',
                'Final Conversion'      : 'No change - no unit detected',
            })
            return original

        else:
            return original

        # ── Build replacement and log ────────────────────────────────────────
        replacement = to_mm_str(mm_raw)
        log_entries.append({
            'File Name'             : filename,
            'Dimension Found'       : original,
            'Raw Conversion result' : f"{mm_raw:.4f} mm",
            'Final Conversion'      : replacement,
        })
        return replacement

    return replacer


# ---------------------------------------------------------------------------
# File processing
# ---------------------------------------------------------------------------
def process_file(filepath, output_dir, log_entries):
    content  = filepath.read_text(encoding='utf-8')
    content  = content.replace('"', '')          # strip all double quotes first
    replacer = make_replacer(filepath.name, log_entries)
    new_content = MASTER_PATTERN.sub(replacer, content)
    (output_dir / filepath.name).write_text(new_content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    script_dir = Path(__file__).parent

    target_folder = (Path(sys.argv[1]) if len(sys.argv) > 1
                     else script_dir / 'Input')
    output_dir    = script_dir / 'Output'
    log_path      = script_dir / 'conversion_log.csv'

    if not target_folder.exists():
        print(f"Error: folder not found: {target_folder}")
        sys.exit(1)

    output_dir.mkdir(exist_ok=True)

    txt_files = sorted(target_folder.glob('*.txt'))
    if not txt_files:
        print(f"No .txt files found in: {target_folder}")
        return

    log_entries = []
    for fp in txt_files:
        process_file(fp, output_dir, log_entries)
        print(f"  Processed: {fp.name}")

    fieldnames = ['File Name', 'Dimension Found', 'Raw Conversion result', 'Final Conversion']
    with open(log_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_entries)

    conversions = sum(1 for e in log_entries
                      if not e['Final Conversion'].startswith('No change'))
    flagged     = len(log_entries) - conversions

    print(f"\nDone. {len(txt_files)} file(s) processed.")
    print(f"  Conversions made : {conversions}")
    print(f"  Flagged (no unit): {flagged}")
    print(f"  Log saved to     : {log_path}")


if __name__ == '__main__':
    main()
