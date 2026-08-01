#!/usr/bin/env python3
"""
Script/Skit/MapData 번역 작업용 GUI.

translate_helper.py와 동일한 2_translated/{script,skit,map}_wip/ 씬 파일들을
대상으로, 파이썬/커맨드라인 없이 브라우저 화면에서 대사를 채워 넣고
저장/검사/병합할 수 있게 해주는 로컬 웹 서버입니다.

실행하면 로컬에서만 열리는 서버가 뜨고 기본 브라우저가 자동으로 열립니다.
외부 네트워크에는 노출되지 않습니다 (127.0.0.1 바인딩).

사용법:
    python translate_gui.py
    (또는 PyInstaller로 빌드한 TranslateGUI.exe 더블클릭)
"""
import csv
import io
import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

if getattr(__import__('sys'), 'frozen', False):
    # PyInstaller onefile bundle: the exe lives where tools/ would live,
    # i.e. directly inside Tales-of-Innocence-R/.
    import sys
    ROOT = Path(sys.executable).resolve().parent
else:
    ROOT = Path(__file__).resolve().parent.parent  # Tales-of-Innocence-R/

WORKDIR = ROOT / '2_translated'

WIP_DIRS = {'script': WORKDIR / 'script_wip', 'skit': WORKDIR / 'skit_wip', 'map': WORKDIR / 'map_wip'}
COLUMNS = {
    'script': ['File', '#', 'Speaker', 'Japanese', 'Korean'],
    'skit': ['File', 'Field', 'Index', 'Speakers', 'Japanese', 'Korean'],
    'map': ['Path', 'Section', '#', 'Speaker', 'Japanese', 'Korean'],
}
MERGE_OUT = {'script': WORKDIR / 'Story.csv', 'skit': WORKDIR / 'Skit.csv', 'map': WORKDIR / 'MapData.csv'}
LABELS = {'script': 'Script (본편 대사)', 'skit': 'Skit (스킷 대사)', 'map': 'MapData (필드 대사)'}

TAG_RE = re.compile(r'\{[^}]*\}')
GLOSSARY_NAMES = {
    'ルカ': '루카', 'アスラ': '아스라', 'イリア': '이리아', 'イナンナ': '이난나',
    'スパーダ': '스파다', 'デュランダル': '듀란달', 'アンジュ': '앙쥬', 'オリフィエル': '오리피엘',
    'リカルド': '리카르도', 'ヒュプノス': '휴프노스', 'エルマーナ': '에르마나', 'ヴリトラ': '브리트라',
    'コンウェイ': '콘웨이', 'キュキュ': '큐큐', 'コーダ': '코다', 'マティウス': '마티우스',
    'チトセ': '치토세', 'サクヤ': '사쿠야', 'バルカン': '바르칸', 'ハスタ': '하스타',
    'ガードル': '가드르', 'ヒンメル': '힘멜', 'ハルトマン': '하르트만',
}


# ------------------------------------------------------------------ data --

def scene_stats(path):
    total = done = 0
    with open(path, encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            total += 1
            if row.get('Korean', '').strip():
                done += 1
    return total, done


def list_files(target):
    wip = WIP_DIRS[target]
    if not wip.exists():
        return []
    out = []
    for fpath in sorted(wip.glob('*.csv')):
        total, done = scene_stats(fpath)
        out.append({'name': fpath.name, 'total': total, 'done': done})
    return out


def summary():
    out = []
    for target, wip in WIP_DIRS.items():
        if not wip.exists():
            continue
        total = done = files_total = files_done = 0
        for fpath in sorted(wip.glob('*.csv')):
            t, d = scene_stats(fpath)
            total += t
            done += d
            files_total += 1
            if t and t == d:
                files_done += 1
        out.append({'target': target, 'label': LABELS[target], 'total': total, 'done': done,
                    'files_total': files_total, 'files_done': files_done})
    return out


def load_scene(target, name):
    fpath = WIP_DIRS[target] / name
    with open(fpath, encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    return {'columns': COLUMNS[target], 'rows': rows}


def save_scene(target, name, rows):
    fpath = WIP_DIRS[target] / name
    cols = COLUMNS[target]
    with open(fpath, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, '') for c in cols})
    return scene_stats(fpath)


def check(target):
    wip = WIP_DIRS[target]
    issues = []
    if not wip.exists():
        return issues
    for fpath in sorted(wip.glob('*.csv')):
        with open(fpath, encoding='utf-8', newline='') as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                jp = row.get('Japanese', '')
                kr = row.get('Korean', '')
                if not kr.strip():
                    continue
                jtags = sorted(TAG_RE.findall(jp))
                ktags = sorted(TAG_RE.findall(kr))
                if jtags != ktags:
                    issues.append({'file': fpath.name, 'line': i, 'kind': '태그 불일치',
                                   'detail': f'원문 {jtags} vs 번역 {ktags}'})
                for jname, kname in GLOSSARY_NAMES.items():
                    if jname in jp and kname not in kr:
                        issues.append({'file': fpath.name, 'line': i, 'kind': '용어 불일치',
                                       'detail': f'"{kname}"({jname}) 누락 -- {kr[:40]}'})
    return issues


def merge(target):
    wip = WIP_DIRS[target]
    if not wip.exists():
        return f'{wip} 없음 -- 먼저 씬 파일이 준비되어야 합니다'
    cols = COLUMNS[target]
    out_path = MERGE_OUT[target]
    total = done = 0
    with open(out_path, 'w', encoding='utf-8', newline='') as out:
        w = csv.writer(out)
        w.writerow(cols)
        for fpath in sorted(wip.glob('*.csv')):
            with open(fpath, encoding='utf-8', newline='') as f:
                for row in csv.DictReader(f):
                    total += 1
                    if row.get('Korean', '').strip():
                        done += 1
                    w.writerow([row.get(c, '') for c in cols])
    return f'{out_path} 생성 완료 ({done}/{total}줄 번역됨)'


# -------------------------------------------------------------- frontend --

INDEX_HTML = """<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<title>번역 작업 도구</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Malgun Gothic", sans-serif; display: flex; height: 100vh; }
  #sidebar { width: 320px; flex: none; border-right: 1px solid #8884; overflow-y: auto; padding: 12px; }
  #main { flex: 1; overflow-y: auto; padding: 16px; }
  h2 { margin: 0 0 8px; font-size: 15px; }
  .target-tab { cursor: pointer; padding: 8px; border-radius: 6px; margin-bottom: 4px; }
  .target-tab.active { background: #4f80ff33; font-weight: bold; }
  .progress-bar { height: 6px; background: #8884; border-radius: 3px; overflow: hidden; margin: 4px 0 10px; }
  .progress-fill { height: 100%; background: #4caf50; }
  .file-item { padding: 6px 8px; cursor: pointer; border-radius: 4px; font-size: 13px; display: flex; justify-content: space-between; }
  .file-item:hover { background: #8882; }
  .file-item.active { background: #4f80ff44; }
  .file-item.done { color: #4caf50; }
  table { width: 100%; border-collapse: collapse; }
  th, td { border: 1px solid #8884; padding: 6px 8px; vertical-align: top; text-align: left; font-size: 13px; }
  th { position: sticky; top: 0; background: Canvas; }
  td.meta { white-space: nowrap; color: #888; font-size: 12px; }
  td.jp { white-space: pre-wrap; max-width: 320px; }
  textarea { width: 100%; min-height: 48px; font-family: inherit; font-size: 13px; resize: vertical; }
  button { padding: 6px 14px; border-radius: 6px; border: 1px solid #8886; background: #4f80ff; color: white; cursor: pointer; }
  button.secondary { background: transparent; color: inherit; }
  #toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; position: sticky; top: 0; background: Canvas; padding: 6px 0; z-index: 2; }
  #status { font-size: 13px; color: #888; }
  .issues { font-size: 12px; margin-top: 10px; max-height: 200px; overflow-y: auto; background: #8881; padding: 8px; border-radius: 6px; }
  .issue { margin-bottom: 4px; }
</style>
</head>
<body>
<div id="sidebar">
  <h2>대상</h2>
  <div id="targets"></div>
  <h2 style="margin-top:16px">씬 목록</h2>
  <div id="files"></div>
</div>
<div id="main">
  <div id="toolbar" style="display:none">
    <strong id="fileTitle"></strong>
    <button id="saveBtn">저장</button>
    <button class="secondary" id="checkBtn">검사</button>
    <button class="secondary" id="mergeBtn">전체 병합</button>
    <span id="status"></span>
  </div>
  <div id="issuesBox" class="issues" style="display:none"></div>
  <table id="table" style="display:none"><thead></thead><tbody></tbody></table>
  <p id="empty">왼쪽에서 대상과 씬을 선택하세요.</p>
</div>
<script>
let curTarget = null, curFile = null, curColumns = [];

async function api(path, opts) {
  const res = await fetch(path, opts);
  return res.json();
}

async function loadTargets() {
  const summary = await api('/api/summary');
  const el = document.getElementById('targets');
  el.innerHTML = '';
  summary.forEach(s => {
    const pct = s.total ? Math.round(s.done / s.total * 100) : 0;
    const div = document.createElement('div');
    div.className = 'target-tab' + (s.target === curTarget ? ' active' : '');
    div.innerHTML = `<div>${s.label}</div>
      <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div style="font-size:12px;color:#888">${s.done}/${s.total}줄 (${pct}%), 씬 ${s.files_done}/${s.files_total}</div>`;
    div.onclick = () => selectTarget(s.target);
    el.appendChild(div);
  });
}

async function selectTarget(target) {
  curTarget = target;
  curFile = null;
  await loadTargets();
  const files = await api('/api/files?target=' + target);
  const el = document.getElementById('files');
  el.innerHTML = '';
  files.forEach(f => {
    const div = document.createElement('div');
    const complete = f.total > 0 && f.total === f.done;
    div.className = 'file-item' + (complete ? ' done' : '');
    div.textContent = `${f.name} (${f.done}/${f.total})`;
    div.onclick = () => selectFile(target, f.name, div);
    el.appendChild(div);
  });
  document.getElementById('table').style.display = 'none';
  document.getElementById('toolbar').style.display = 'none';
  document.getElementById('empty').style.display = 'block';
}

async function selectFile(target, name, el) {
  document.querySelectorAll('.file-item').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
  curFile = name;
  const data = await api(`/api/scene?target=${target}&file=${encodeURIComponent(name)}`);
  curColumns = data.columns;
  const thead = document.querySelector('#table thead');
  const tbody = document.querySelector('#table tbody');
  thead.innerHTML = '<tr>' + curColumns.map(c => `<th>${c}</th>`).join('') + '</tr>';
  tbody.innerHTML = '';
  data.rows.forEach((row, i) => {
    const tr = document.createElement('tr');
    curColumns.forEach(c => {
      const td = document.createElement('td');
      if (c === 'Korean') {
        td.innerHTML = `<textarea data-row="${i}" data-col="${c}">${escapeHtml(row[c] || '')}</textarea>`;
      } else if (c === 'Japanese') {
        td.className = 'jp';
        td.textContent = row[c] || '';
      } else {
        td.className = 'meta';
        td.textContent = row[c] || '';
      }
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  window._rows = data.rows;
  document.getElementById('fileTitle').textContent = `${target} / ${name}`;
  document.getElementById('table').style.display = 'table';
  document.getElementById('toolbar').style.display = 'flex';
  document.getElementById('empty').style.display = 'none';
  document.getElementById('issuesBox').style.display = 'none';
  setStatus('');
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function setStatus(msg) { document.getElementById('status').textContent = msg; }

async function saveCurrent() {
  const rows = window._rows.map((row, i) => {
    const ta = document.querySelector(`textarea[data-row="${i}"]`);
    return { ...row, Korean: ta ? ta.value : row.Korean };
  });
  const res = await api(`/api/scene?target=${curTarget}&file=${encodeURIComponent(curFile)}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rows })
  });
  setStatus(`저장됨 (${res.done}/${res.total})`);
  await selectTarget(curTarget);
}

async function runCheck() {
  setStatus('검사 중...');
  const res = await api('/api/check?target=' + curTarget, { method: 'POST' });
  const box = document.getElementById('issuesBox');
  if (!res.issues.length) {
    box.style.display = 'block';
    box.innerHTML = '문제 없음 (0건)';
  } else {
    box.style.display = 'block';
    box.innerHTML = `${res.issues.length}건 발견<br>` + res.issues.slice(0, 100).map(
      it => `<div class="issue">${it.file}:${it.line} -- ${it.kind}: ${escapeHtml(it.detail)}</div>`
    ).join('');
  }
  setStatus('');
}

async function runMerge() {
  setStatus('병합 중...');
  const res = await api('/api/merge?target=' + curTarget, { method: 'POST' });
  setStatus(res.message);
}

document.getElementById('saveBtn').onclick = saveCurrent;
document.getElementById('checkBtn').onclick = runCheck;
document.getElementById('mergeBtn').onclick = runMerge;

loadTargets().then(() => {
  const first = document.querySelector('.target-tab');
  if (first) first.click();
});
</script>
</body></html>
"""


# --------------------------------------------------------------- server --

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == '/':
            body = INDEX_HTML.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path == '/api/summary':
            self._json(summary())
        elif parsed.path == '/api/files':
            target = qs.get('target', [''])[0]
            self._json(list_files(target))
        elif parsed.path == '/api/scene':
            target = qs.get('target', [''])[0]
            name = qs.get('file', [''])[0]
            self._json(load_scene(target, name))
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''
        if parsed.path == '/api/scene':
            target = qs.get('target', [''])[0]
            name = qs.get('file', [''])[0]
            data = json.loads(body)
            total, done = save_scene(target, name, data['rows'])
            self._json({'ok': True, 'total': total, 'done': done})
        elif parsed.path == '/api/check':
            target = qs.get('target', [''])[0]
            self._json({'issues': check(target)})
        elif parsed.path == '/api/merge':
            target = qs.get('target', [''])[0]
            self._json({'message': merge(target)})
        else:
            self.send_error(404)


DEFAULT_PORT = 8765


def main():
    server = None
    port = DEFAULT_PORT
    for attempt in range(20):
        try:
            server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            port += 1
    if server is None:
        print('사용 가능한 포트를 찾지 못했습니다. 프로그램을 다시 실행해보세요.')
        input('엔터를 누르면 창이 닫힙니다...')
        return

    url = f'http://127.0.0.1:{port}/'
    print('=' * 50)
    print(f'번역 작업 GUI 서버가 시작되었습니다.')
    print(f'주소: {url}')
    print('브라우저가 자동으로 열리지 않으면 위 주소를 직접 열어주세요.')
    print('이 창을 닫으면 서버도 함께 종료됩니다.')
    print('=' * 50)
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'오류 발생: {e}')
        input('엔터를 누르면 창이 닫힙니다...')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'예상치 못한 오류로 종료되었습니다: {e}')
        input('엔터를 누르면 창이 닫힙니다...')
