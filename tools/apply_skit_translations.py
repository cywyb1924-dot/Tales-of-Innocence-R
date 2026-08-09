#!/usr/bin/env python3
"""
Apply a batch of Korean translations to 2_translated/skit_wip/*.csv files
without hand-writing CSV (avoids the comma-escaping bugs found earlier in
this project). Input is a JSON file:

    {
        "0335.dat.csv": ["translation for 1st blank row", "translation for 2nd blank row", ...],
        "1022.dat.csv": [...],
        ...
    }

For each named file, rows are scanned top to bottom; each row whose Japanese
column is non-empty and Korean column is empty consumes the next string from
the list, in order. Row count of blanks must exactly match the list length
(fails loudly otherwise, so a mismatch can't silently misalign rows).

Usage:
    python tools/apply_skit_translations.py path/to/batch.json
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIP = ROOT / '2_translated' / 'skit_wip'


def apply_one(fname, translations):
    fpath = WIP / fname
    with open(fpath, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    header, data = rows[0], rows[1:]
    idx = {name: i for i, name in enumerate(header)}
    ja_i, ko_i = idx['Japanese'], idx['Korean']

    blanks = [i for i, row in enumerate(data) if row[ja_i].strip() and not row[ko_i].strip()]
    if len(blanks) != len(translations):
        raise SystemExit(
            f"{fname}: expected {len(blanks)} translations, got {len(translations)}"
        )
    for i, text in zip(blanks, translations):
        data[i][ko_i] = text

    with open(fpath, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)
    return len(blanks)


def main():
    batch_path = Path(sys.argv[1])
    batch = json.loads(batch_path.read_text(encoding='utf-8'))
    total = 0
    for fname, translations in batch.items():
        n = apply_one(fname, translations)
        total += n
        print(f"  {fname}: {n} lines filled")
    print(f"Applied {total} lines across {len(batch)} files")


if __name__ == '__main__':
    main()
