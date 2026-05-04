import os
import re
import csv
from collections import defaultdict

# === CONFIGURATION ===
GERMAN_SCRIPTS_DIR = r"C:\\Translations\Advanced Sketching\\German Scripts"
ENGLISH_SCRIPTS_DIR = r"C:\\Translations\Advanced Sketching\\English Scripts"  # <-- Enter path to English scripts folder here

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DETECTED_UNITS_CSV = os.path.join(SCRIPT_DIR, "UnitDetect", "detectedunits.csv")
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "UnitDetect", "unit_sync_results.csv")

TOLERANCE_PERCENT = 5


# ── shared helpers ────────────────────────────────────────────────────────────

def is_inch_dimension(text):
    lower = text.lower()
    return bool(re.search(r'\binch(es)?\b|-inch\b|\bin\b|in\.', lower))


def parse_inch_value(text):
    m = re.search(r'(\d+(?:\.\d+)?)', text)
    return float(m.group(1)) if m else None


def extract_numeric_code(filename):
    matches = re.findall(r'(\d{2}_\d{2})', filename)
    return matches[-1] if matches else None


def find_german_script(numeric_code, german_dir):
    for fname in os.listdir(german_dir):
        if fname.startswith(numeric_code) and fname.lower().endswith('.txt'):
            return fname
    return None


def extract_numbers(text):
    return [float(m) for m in re.findall(r'\b\d+(?:\.\d+)?\b', text)]


def find_match(numbers, target, tolerance_pct=5):
    for n in numbers:
        if abs(n - target) < 1e-6:
            return n, 'exact match'
    tolerance = target * (tolerance_pct / 100)
    candidates = [(abs(n - target), n) for n in numbers if abs(n - target) <= tolerance]
    if candidates:
        candidates.sort()
        return candidates[0][1], f'closest match (within {tolerance_pct}%)'
    return None, 'not found'


def load_detected_units(csv_path):
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2:
                rows.append((parts[0].strip(), parts[1].strip()))
    return rows


def format_mm(value):
    v = int(value) if value == int(value) else value
    return f"{v} milimeters"


# ── Step 1: Unit SYNC ─────────────────────────────────────────────────────────

def run_unit_sync():
    if not GERMAN_SCRIPTS_DIR:
        print("ERROR: Please set GERMAN_SCRIPTS_DIR at the top of this script.")
        return
    if not os.path.isdir(GERMAN_SCRIPTS_DIR):
        print(f"ERROR: German scripts directory not found: {GERMAN_SCRIPTS_DIR}")
        return

    detected = load_detected_units(DETECTED_UNITS_CSV)
    german_text_cache = {}
    results = []

    for english_filename, dimension_str in detected:
        if not is_inch_dimension(dimension_str):
            continue
        inch_value = parse_inch_value(dimension_str)
        if inch_value is None:
            continue

        mm_target = inch_value * 25
        numeric_code = extract_numeric_code(english_filename)
        if not numeric_code:
            results.append({
                'German Script': '',
                'English Script': english_filename,
                'Dimension (in)': dimension_str,
                'mm Target (x25)': round(mm_target, 4),
                'German Value Found': '',
                'Status': 'no numeric code in English filename',
            })
            continue

        german_filename = find_german_script(numeric_code, GERMAN_SCRIPTS_DIR)
        if not german_filename:
            results.append({
                'German Script': f'[no match for {numeric_code}]',
                'English Script': english_filename,
                'Dimension (in)': dimension_str,
                'mm Target (x25)': round(mm_target, 4),
                'German Value Found': '',
                'Status': 'German script not found',
            })
            continue

        german_path = os.path.join(GERMAN_SCRIPTS_DIR, german_filename)
        if german_path not in german_text_cache:
            with open(german_path, encoding='utf-8', errors='replace') as f:
                german_text_cache[german_path] = f.read()

        numbers = extract_numbers(german_text_cache[german_path])
        matched_value, status = find_match(numbers, mm_target, TOLERANCE_PERCENT)

        results.append({
            'German Script': german_filename,
            'English Script': english_filename,
            'Dimension (in)': dimension_str,
            'mm Target (x25)': round(mm_target, 4),
            'German Value Found': matched_value if matched_value is not None else '',
            'Status': status,
        })

    fieldnames = [
        'German Script', 'English Script', 'Dimension (in)',
        'mm Target (x25)', 'German Value Found', 'Status',
    ]
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    found = sum(1 for r in results if 'match' in r['Status'])
    print(f"Done. {len(results)} inch dimension(s) processed.")
    print(f"  Matched in German scripts: {found}")
    print(f"  Not found: {len(results) - found}")
    print(f"Results saved to: {OUTPUT_CSV}")


# ── Step 2: Unit Update ───────────────────────────────────────────────────────

def run_unit_update():
    if not ENGLISH_SCRIPTS_DIR:
        print("ERROR: Please set ENGLISH_SCRIPTS_DIR at the top of this script.")
        return
    if not os.path.isdir(ENGLISH_SCRIPTS_DIR):
        print(f"ERROR: English scripts directory not found: {ENGLISH_SCRIPTS_DIR}")
        return
    if not os.path.exists(OUTPUT_CSV):
        print(f"ERROR: {OUTPUT_CSV} not found. Run Step 1 first.")
        return

    # Build unique replacements per file: {filename: {dim_str: replacement_text}}
    file_replacements = defaultdict(dict)
    with open(OUTPUT_CSV, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if 'match' not in row['Status']:
                continue
            german_value = row['German Value Found']
            if not german_value:
                continue
            english_file = row['English Script']
            dim_str = row['Dimension (in)']
            replacement = format_mm(float(german_value))
            file_replacements[english_file][dim_str] = replacement

    if not file_replacements:
        print("No matched dimensions found in unit_sync_results.csv. Nothing to replace.")
        return

    updated_files = 0
    total_replacements = 0

    for english_file, subs in file_replacements.items():
        path = os.path.join(ENGLISH_SCRIPTS_DIR, english_file)
        if not os.path.exists(path):
            print(f"  WARNING: {english_file} not found in English scripts dir — skipped.")
            continue

        with open(path, encoding='utf-8', errors='replace') as f:
            content = f.read()

        for dim_str, replacement in subs.items():
            count = len(re.findall(re.escape(dim_str), content, flags=re.IGNORECASE))
            content = re.sub(re.escape(dim_str), replacement, content, flags=re.IGNORECASE)
            if count:
                print(f"  {english_file}: '{dim_str}' → '{replacement}' ({count} occurrence(s))")
                total_replacements += count

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        updated_files += 1

    print(f"\nDone. {updated_files} file(s) updated, {total_replacements} replacement(s) made.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("Unit SYNC Tool")
    print("  1. Find matching dimensions  (Unit SYNC  — reads detectedunits.csv, writes unit_sync_results.csv)")
    print("  2. Replace dimensions        (Unit Update — reads unit_sync_results.csv, edits English scripts)")
    choice = input("\nSelect step (1 or 2): ").strip()

    if choice == '1':
        run_unit_sync()
    elif choice == '2':
        run_unit_update()
    else:
        print("Invalid choice. Enter 1 or 2.")


if __name__ == '__main__':
    main()
