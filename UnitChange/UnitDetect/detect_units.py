import os
import re
import csv

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100,
}

UNIT_PATTERNS = [
    (r"inch(?:es)?", "inches"),
    (r"in\.", "inches"),
    (r"(?<!\w)in(?!\w)", "inches"),
    (r"feet", "feet"),
    (r"foot", "feet"),
    (r"ft\.", "feet"),
    (r"(?<!\w)ft(?!\w)", "feet"),
    (r"degrees?", "degrees"),
    (r"deg\.", "degrees"),
    (r"(?<!\w)deg(?!\w)", "degrees"),
    (r"°", "degrees"),
    (r"millimeters?", "millimeters"),
    (r"(?<!\w)mm(?!\w)", "millimeters"),
    (r"centimeters?", "centimeters"),
    (r"(?<!\w)cm(?!\w)", "centimeters"),
    (r"(?<!\w)meters?(?!\w)", "meters"),
    (r"(?<!\w)m(?!\w)", "meters"),
]

UNIT_REGEX = re.compile(
    r"(" + "|".join(p for p, _ in UNIT_PATTERNS) + r")",
    re.IGNORECASE,
)

UNIT_LABEL_MAP = {p: label for p, label in UNIT_PATTERNS}

EXCLUSION_WORDS = {"types", "kinds", "levels", "main"}

NUMERIC_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s*[-]?\s*", re.IGNORECASE)
SPELLED_NUMBER_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in WORD_TO_NUM) + r")\s+",
    re.IGNORECASE,
)


def resolve_unit_label(unit_str):
    for pattern, label in UNIT_PATTERNS:
        if re.fullmatch(pattern, unit_str, re.IGNORECASE):
            return label
    return unit_str.lower()


def find_matches_in_line(line):
    matches = []
    used = set()

    # Numeric value followed by optional dash/space then unit
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*[-]?\s*(" + "|".join(p for p, _ in UNIT_PATTERNS) + r")",
        line,
        re.IGNORECASE,
    ):
        unit_label = resolve_unit_label(m.group(2))
        matches.append((m.start(), m.group(0).strip(), unit_label))
        used.update(range(m.start(), m.end()))

    # Spelled-out number followed by unit
    for m in re.finditer(
        r"\b(" + "|".join(re.escape(w) for w in WORD_TO_NUM) + r")\s+("
        + "|".join(p for p, _ in UNIT_PATTERNS) + r")",
        line,
        re.IGNORECASE,
    ):
        if m.start() not in used:
            unit_label = resolve_unit_label(m.group(2))
            matches.append((m.start(), m.group(0).strip(), unit_label))
            used.update(range(m.start(), m.end()))

    # Any bare number not followed by an exclusion word and not already captured
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\b", line):
        if m.start() in used:
            continue
        after = line[m.end():].lstrip(" \t-")
        next_word_m = re.match(r"([A-Za-z]+)", after)
        if next_word_m:
            next_word = next_word_m.group(1).lower()
            if next_word in EXCLUSION_WORDS:
                continue
        matches.append((m.start(), m.group(0).strip(), "unknown"))

    matches.sort(key=lambda x: x[0])
    return [(text, unit) for _, text, unit in matches]


def detect_units_in_directory(directory):
    rows = []
    for filename in sorted(os.listdir(directory)):
        if not filename.lower().endswith(".txt"):
            continue
        filepath = os.path.join(directory, filename)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                for matched_text, unit in find_matches_in_line(line.rstrip()):
                    rows.append({
                        "File Name": filename,
                        "Line Number": line_num,
                        "Matched Text": matched_text,
                        "Unit": unit,
                    })
    return rows


def main():
    directory = input("Enter the path to the folder containing .txt script files: ").strip()
    if not os.path.isdir(directory):
        print(f"Directory not found: {directory}")
        return

    rows = detect_units_in_directory(directory)

    if not rows:
        print("No matches found.")
        return

    output_path = os.path.join(directory, "unit_detections.csv")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["File Name", "Line Number", "Matched Text", "Unit"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done. {len(rows)} match(es) found across {len({r['File Name'] for r in rows})} file(s).")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
