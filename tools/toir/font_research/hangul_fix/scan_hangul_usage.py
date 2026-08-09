import csv, glob, io, json, sys
from collections import Counter

ROOT = r"C:\Users\cywyb\Downloads\claude\patch\Tales-of-Innocence-R"
files = glob.glob(ROOT + r"\2_translated\**\*.csv", recursive=True)

counter = Counter()
col_names_seen = Counter()
rows_scanned = 0
files_scanned = 0
errors = []

for fp in files:
    try:
        with io.open(fp, encoding='utf-8-sig', newline='') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                continue
            # find any column that looks like it holds Korean/translated text
            target_cols = [i for i, h in enumerate(header) if h.strip().lower() in ('korean', 'ko', 'kr', 'translation', 'translated')]
            for i in target_cols:
                col_names_seen[header[i]] += 1
            if not target_cols:
                continue
            for row in reader:
                rows_scanned += 1
                for i in target_cols:
                    if i < len(row):
                        text = row[i]
                        for ch in text:
                            cc = ord(ch)
                            if 0xAC00 <= cc <= 0xD7A3:  # Hangul syllables block
                                counter[cc] += 1
        files_scanned += 1
    except Exception as e:
        errors.append((fp, str(e)))

out = {
    'files_total': len(files),
    'files_scanned': files_scanned,
    'rows_scanned': rows_scanned,
    'unique_hangul_chars': len(counter),
    'col_names_seen': dict(col_names_seen),
    'errors_count': len(errors),
}

with io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\hangul_usage_summary.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# save full char list (sorted by codepoint) with counts
with io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\hangul_usage_chars.tsv', 'w', encoding='utf-8') as f:
    f.write("codepoint_hex\tchar\tcount\n")
    for cc, cnt in sorted(counter.items()):
        f.write(f"{cc:04X}\t{chr(cc)}\t{cnt}\n")

with io.open(r'C:\Users\cywyb\.claude\jobs\8884f3d3\tmp\hangul_usage_errors.txt', 'w', encoding='utf-8') as f:
    for fp, e in errors[:50]:
        f.write(f"{fp}: {e}\n")

print("done")
print(json.dumps(out, ensure_ascii=False, indent=2))
