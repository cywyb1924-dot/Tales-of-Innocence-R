#!/usr/bin/env python3
"""
Translation workflow helper for Script.csv / Skit.csv.

Splits the raw extracted narrative CSVs (1_extracted/Script.csv,
1_extracted/Skit.csv) into small per-scene working files under
2_translated/script_wip/ and 2_translated/skit_wip/, so a human translator
(or team) can work through them incrementally rather than as one giant file.
Also tracks progress, validates control-tag/glossary consistency, and merges
finished work back into the single CSV the recompile pipeline expects
(toir/formats/script/recompile.py reads 2_translated/Story.csv,
toir/formats/skits/recompile.py reads 2_translated/Skit.csv).

This script only prepares/checks/merges files -- it does not translate
anything itself. Fill in the "Korean" column of the per-scene files by hand.

Also covers MapData.csv (field/dungeon NPC dialogue), same shape as Script.csv
but with an extra Section column (toir/formats/mapdata/recompile.py reads
2_translated/MapData.csv with header Path,Section,#,Speaker,Japanese,Korean).

Usage:
    python translate_helper.py prep-script    # split Script.csv into scenes
    python translate_helper.py prep-skit      # split Skit.csv into skits
    python translate_helper.py prep-map       # split MapData.csv into scenes
    python translate_helper.py progress       # show completion %
    python translate_helper.py check script   # validate tags/glossary
    python translate_helper.py check skit
    python translate_helper.py check map
    python translate_helper.py merge-script   # rebuild Story.csv for recompile
    python translate_helper.py merge-skit     # rebuild Skit.csv for recompile
    python translate_helper.py merge-map      # rebuild MapData.csv for recompile
"""
import argparse
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # Tales-of-Innocence-R/
EXTRACTED = ROOT / '1_extracted'
WORKDIR = ROOT / '2_translated'

TAG_RE = re.compile(r'\{[^}]*\}')

# Canonical Korean spellings from GLOSSARY_KO.md, used by `check` to flag
# any scene where a known name shows up in the Japanese but the matching
# Korean spelling doesn't appear in the translation.
GLOSSARY_NAMES = {
    'ルカ': '루카', 'アスラ': '아스라', 'イリア': '이리아', 'イナンナ': '이난나',
    'スパーダ': '스파다', 'デュランダル': '듀란달', 'アンジュ': '앙쥬', 'オリフィエル': '오리피엘',
    'リカルド': '리카르도', 'ヒュプノス': '휴프노스', 'エルマーナ': '에르마나', 'ヴリトラ': '브리트라',
    'コンウェイ': '콘웨이', 'キュキュ': '큐큐', 'コーダ': '코다', 'マティウス': '마티우스',
    'チトセ': '치토세', 'サクヤ': '사쿠야', 'バルカン': '바르칸', 'ハスタ': '하스타',
    'ガードル': '가드르', 'ヒンメル': '힘멜', 'ハルトマン': '하르트만',
}


def safe_name(s):
    return re.sub(r'[^A-Za-z0-9._-]', '_', s)


# ---------------------------------------------------------------- script --

def prep_script():
    out_dir = WORKDIR / 'script_wip'
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes = {}
    with open(EXTRACTED / 'Script.csv', encoding='utf-8', newline='') as f:
        # Script.csv has no header row (see toir/formats/script/extract.py)
        for row in csv.DictReader(f, fieldnames=['path', 'id', 'speaker', 'text']):
            scenes.setdefault(row['path'], []).append(row)

    written = 0
    for path, rows in scenes.items():
        outpath = out_dir / (safe_name(path) + '.csv')
        if outpath.exists():
            continue  # never clobber in-progress translation work
        with open(outpath, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['File', '#', 'Speaker', 'Japanese', 'Korean'])
            for row in rows:
                w.writerow([path, row['id'], row['speaker'], row['text'], ''])
        written += 1
    print(f'wrote {written} new scene files to {out_dir} ({len(scenes)} scenes total, '
          f'{len(scenes) - written} already existed and were left untouched)')


def merge_script():
    src_dir = WORKDIR / 'script_wip'
    if not src_dir.exists():
        print(f'{src_dir} does not exist -- run prep-script first')
        return
    out_path = WORKDIR / 'Story.csv'
    total = done = 0
    with open(out_path, 'w', encoding='utf-8', newline='') as out:
        w = csv.writer(out)
        w.writerow(['File', '#', 'Speaker', 'Japanese', 'Korean'])
        for fpath in sorted(src_dir.glob('*.csv')):
            with open(fpath, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    total += 1
                    if row['Korean'].strip():
                        done += 1
                    w.writerow([row['File'], row['#'], row['Speaker'], row['Japanese'], row['Korean']])
    print(f'merged {total} lines into {out_path} ({done} translated, {total - done} still empty)')


# ------------------------------------------------------------------- map --

def prep_map():
    out_dir = WORKDIR / 'map_wip'
    out_dir.mkdir(parents=True, exist_ok=True)
    scenes = {}
    with open(EXTRACTED / 'MapData.csv', encoding='utf-8', newline='') as f:
        # MapData.csv has no header row (see toir/formats/mapdata/extract.py)
        for row in csv.DictReader(f, fieldnames=['path', 'section', 'id', 'speaker', 'text']):
            scenes.setdefault(row['path'], []).append(row)

    written = 0
    for path, rows in scenes.items():
        outpath = out_dir / (safe_name(path) + '.csv')
        if outpath.exists():
            continue
        with open(outpath, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Path', 'Section', '#', 'Speaker', 'Japanese', 'Korean'])
            for row in rows:
                w.writerow([path, row['section'], row['id'], row['speaker'], row['text'], ''])
        written += 1
    print(f'wrote {written} new scene files to {out_dir} ({len(scenes)} scenes total, '
          f'{len(scenes) - written} already existed and were left untouched)')


def merge_map():
    src_dir = WORKDIR / 'map_wip'
    if not src_dir.exists():
        print(f'{src_dir} does not exist -- run prep-map first')
        return
    out_path = WORKDIR / 'MapData.csv'
    total = done = 0
    with open(out_path, 'w', encoding='utf-8', newline='') as out:
        w = csv.writer(out)
        w.writerow(['Path', 'Section', '#', 'Speaker', 'Japanese', 'Korean'])
        for fpath in sorted(src_dir.glob('*.csv')):
            with open(fpath, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    total += 1
                    if row['Korean'].strip():
                        done += 1
                    w.writerow([row['Path'], row['Section'], row['#'], row['Speaker'],
                                row['Japanese'], row['Korean']])
    print(f'merged {total} lines into {out_path} ({done} translated, {total - done} still empty)')


# ------------------------------------------------------------------ skit --

def prep_skit():
    out_dir = WORKDIR / 'skit_wip'
    out_dir.mkdir(parents=True, exist_ok=True)
    skits = {}
    with open(EXTRACTED / 'Skit.csv', encoding='utf-8', newline='') as f:
        # Skit.csv DOES have a header row: R,File,Field,Index,Speakers,Japanese
        for row in csv.DictReader(f):
            skits.setdefault(row['File'], []).append(row)

    written = 0
    for file, rows in skits.items():
        outpath = out_dir / (safe_name(file) + '.csv')
        if outpath.exists():
            continue
        with open(outpath, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['File', 'Field', 'Index', 'Speakers', 'Japanese', 'Korean'])
            for row in rows:
                w.writerow([row['File'], row['Field'], row['Index'], row['Speakers'], row['Japanese'], ''])
        written += 1
    print(f'wrote {written} new skit files to {out_dir} ({len(skits)} skits total, '
          f'{len(skits) - written} already existed and were left untouched)')


def merge_skit():
    src_dir = WORKDIR / 'skit_wip'
    if not src_dir.exists():
        print(f'{src_dir} does not exist -- run prep-skit first')
        return
    out_path = WORKDIR / 'Skit.csv'
    total = done = 0
    with open(out_path, 'w', encoding='utf-8', newline='') as out:
        w = csv.writer(out)
        w.writerow(['File', 'Field', 'Index', 'Speakers', 'Japanese', 'Korean'])
        for fpath in sorted(src_dir.glob('*.csv')):
            with open(fpath, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    total += 1
                    if row['Korean'].strip():
                        done += 1
                    w.writerow([row['File'], row['Field'], row['Index'], row['Speakers'],
                                row['Japanese'], row['Korean']])
    print(f'merged {total} lines into {out_path} ({done} translated, {total - done} still empty)')


# -------------------------------------------------------------- progress --

def progress():
    for label, wip_dir in [('Script', WORKDIR / 'script_wip'), ('Skit', WORKDIR / 'skit_wip'),
                           ('MapData', WORKDIR / 'map_wip')]:
        if not wip_dir.exists():
            print(f'{label}: not prepped yet (run prep-{label.lower()})')
            continue
        total = done = files_done = files_total = 0
        for fpath in sorted(wip_dir.glob('*.csv')):
            files_total += 1
            file_lines = file_done = 0
            with open(fpath, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    total += 1
                    file_lines += 1
                    if row['Korean'].strip():
                        done += 1
                        file_done += 1
            if file_lines and file_done == file_lines:
                files_done += 1
        pct = (done / total * 100) if total else 0
        print(f'{label}: {done}/{total} lines translated ({pct:.1f}%), '
              f'{files_done}/{files_total} scenes fully complete')


# ------------------------------------------------------------------ check --

def check(target):
    wip_dir = WORKDIR / f'{target}_wip'
    if not wip_dir.exists():
        print(f'{wip_dir} does not exist -- run prep-{target} first')
        return
    issues = []
    for fpath in sorted(wip_dir.glob('*.csv')):
        with open(fpath, encoding='utf-8', newline='') as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                jp = row.get('Japanese', '')
                kr = row.get('Korean', '')
                if not kr.strip():
                    continue  # untranslated rows have nothing to check yet
                jtags = sorted(TAG_RE.findall(jp))
                ktags = sorted(TAG_RE.findall(kr))
                if jtags != ktags:
                    issues.append((fpath.name, i, 'TAG MISMATCH', jtags, ktags))
                for jname, kname in GLOSSARY_NAMES.items():
                    if jname in jp and kname not in kr:
                        issues.append((fpath.name, i, f'expected "{kname}" (for {jname})', kr[:50]))
    print(f'{len(issues)} issue(s) found')
    for it in issues[:200]:
        print(it)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('prep-script', help='split 1_extracted/Script.csv into per-scene files')
    sub.add_parser('prep-skit', help='split 1_extracted/Skit.csv into per-skit files')
    sub.add_parser('prep-map', help='split 1_extracted/MapData.csv into per-scene files')
    sub.add_parser('merge-script', help='rebuild 2_translated/Story.csv from script_wip/')
    sub.add_parser('merge-skit', help='rebuild 2_translated/Skit.csv from skit_wip/')
    sub.add_parser('merge-map', help='rebuild 2_translated/MapData.csv from map_wip/')
    sub.add_parser('progress', help='show translation completion percentage')
    c = sub.add_parser('check', help='validate control tags and glossary consistency')
    c.add_argument('target', choices=['script', 'skit', 'map'])
    args = p.parse_args()

    {
        'prep-script': prep_script,
        'prep-skit': prep_skit,
        'prep-map': prep_map,
        'merge-script': merge_script,
        'merge-skit': merge_skit,
        'merge-map': merge_map,
        'progress': progress,
    }.get(args.cmd, lambda: check(args.target))()


if __name__ == '__main__':
    main()
