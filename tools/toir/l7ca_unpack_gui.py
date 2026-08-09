"""
테일즈 오브 이노센스 R 한글패치 - L7C 압축 해제 도구 (GUI 버전)

xdelta로 패치한 `toidata_release.l7c`를 게임이 실제로 읽는 loose 파일
(`_Data/` 트리)로 압축 해제하는 일반 사용자용 도구입니다. 커맨드라인이
익숙하지 않은 사용자를 위해 `l7ca_unpack.py`(개발자/커맨드라인용)를
tkinter GUI로 감쌌습니다 — 압축 해제 로직 자체는 완전히 동일합니다.

## 실행 방법

Python이 설치되어 있어야 합니다(설치법은 PATCH_적용법.md 참고). 이 파일이
있는 폴더에서:

    python l7ca_unpack_gui.py

또는 파일 탐색기에서 이 파일을 더블클릭해도 실행됩니다(.py 파일이
python.exe에 연결되어 있는 경우).
"""
import struct
import zlib
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk


HEADER_FMT = '<IIiiiIiiiiii'
HEADER_SIZE = struct.calcsize(HEADER_FMT)
FS_ENTRY_FMT = '<iIiiq'
FS_ENTRY_SIZE = struct.calcsize(FS_ENTRY_FMT)
FILE_ENTRY_FMT = '<iiiiiI'
FILE_ENTRY_SIZE = struct.calcsize(FILE_ENTRY_FMT)
CHUNK_ENTRY_FMT = '<IHH'
CHUNK_ENTRY_SIZE = struct.calcsize(CHUNK_ENTRY_FMT)


def taiko_decompress(data, prev=None):
    """psvita-l7ctool/TaikoCompression.cs의 Decompress()를 그대로 이식."""
    output = bytearray(prev) if prev else bytearray()
    pos = 0
    n = len(data)
    while pos < n:
        c = data[pos]
        pos += 1

        if c > 0xbf:
            length = (c - 0xbe) * 2
            flag = data[pos]
            pos += 1
            back = ((flag & 0x7f) << 8) + data[pos] + 1
            pos += 1
            if flag & 0x80:
                length += 1
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c > 0x7f:
            length = (c >> 2) & 0x1f
            back = ((c & 0x3) << 8) + data[pos] + 1
            pos += 1
            if c & 0x80:
                length += 3
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c > 0x3f:
            length = (c >> 4) - 2
            back = (c & 0x0f) + 1
            end = len(output)
            for i in range(length):
                output.append(output[end - back + i])
        elif c == 0x00:
            flag = data[pos]
            pos += 1
            flag2 = 0
            length = 0x40
            if (flag & 0x80) == 0:
                flag2 = data[pos]
                pos += 1
                length = 0xbf + flag2 + (flag << 8)
                if flag == 0 and flag2 == 0 and pos < n and data[pos] == 0x00:
                    break
            else:
                length += flag & 0x7f
            output.extend(data[pos:pos + length])
            pos += length
        else:
            output.extend(data[pos:pos + c])
            pos += c

    return bytes(output)


def parse_header(f):
    f.seek(0)
    (magic, unk, archive_size, metadata_offset, metadata_size, unk2,
     filesystem_entries, folders, files, chunks, string_table_size, unk4) = \
        struct.unpack(HEADER_FMT, f.read(HEADER_SIZE))
    if magic != 0x4143374c:
        raise ValueError('L7CA 아카이브 형식이 아닙니다 (파일이 손상되었거나 잘못된 파일입니다)')
    return dict(metadata_offset=metadata_offset, filesystem_entries=filesystem_entries,
                files=files, string_table_size=string_table_size)


def read_strings(f, filesize, string_table_size):
    base = filesize - string_table_size
    f.seek(base)
    blob = f.read(string_table_size)
    strings = {}
    pos = 0
    while pos < len(blob):
        ln = blob[pos]
        strings[pos] = blob[pos + 1:pos + 1 + ln].decode('utf-8', 'replace')
        pos += 1 + ln
    return strings


def build_name_to_id(f, header, filesize):
    strings = read_strings(f, filesize, header['string_table_size'])
    f.seek(header['metadata_offset'])
    name_to_id = {}
    for _ in range(header['filesystem_entries']):
        eid, ehash, folder_off, filename_off, timestamp = \
            struct.unpack(FS_ENTRY_FMT, f.read(FS_ENTRY_SIZE))
        if eid == -1:
            continue
        name = f"{strings.get(folder_off, '?')}/{strings.get(filename_off, '?')}"
        name_to_id[name] = eid
    return name_to_id


def file_entry_pos(header, target_id):
    file_entries_start = header['metadata_offset'] + \
        header['filesystem_entries'] * FS_ENTRY_SIZE
    return file_entries_start + target_id * FILE_ENTRY_SIZE


def chunk_table_start(header):
    return header['metadata_offset'] + \
        header['filesystem_entries'] * FS_ENTRY_SIZE + \
        header['files'] * FILE_ENTRY_SIZE


def unpack(l7c_path, out_dir, prefix_filter='_Data/', log=print, progress=None, should_stop=None):
    l7c_path = Path(l7c_path)
    out_dir = Path(out_dir)

    with open(l7c_path, 'rb') as f:
        filesize = l7c_path.stat().st_size
        header = parse_header(f)
        name_to_id = build_name_to_id(f, header, filesize)
        ctable_start = chunk_table_start(header)

        targets = sorted(n for n in name_to_id if n.startswith(prefix_filter) and '?' not in n)
        total = len(targets)
        log(f"'{prefix_filter}' 아래 {total}개 파일을 '{out_dir}'로 압축 해제합니다...")

        written = 0
        failed = []
        for i, name in enumerate(targets):
            if should_stop and should_stop():
                log("사용자가 중단했습니다.")
                return False

            tid = name_to_id[name]
            pos = file_entry_pos(header, tid)
            f.seek(pos)
            compressed_size, raw_size, chunk_idx, chunk_count, offset, crc32 = \
                struct.unpack(FILE_ENTRY_FMT, f.read(FILE_ENTRY_SIZE))

            chunk_infos = []
            for c in range(chunk_count):
                f.seek(ctable_start + (chunk_idx + c) * CHUNK_ENTRY_SIZE)
                chunk_size_field, unk, chunk_id = struct.unpack(CHUNK_ENTRY_FMT, f.read(CHUNK_ENTRY_SIZE))
                chunk_infos.append((bool(chunk_size_field & 0x80000000), chunk_size_field & 0x00ffffff))

            f.seek(offset)
            blob = f.read(compressed_size)

            try:
                accumulated = bytearray()
                blob_pos = 0
                for is_compressed, chunk_byte_len in chunk_infos:
                    chunk_data = blob[blob_pos:blob_pos + chunk_byte_len]
                    blob_pos += chunk_byte_len
                    if is_compressed:
                        accumulated = bytearray(taiko_decompress(bytes(chunk_data), prev=bytes(accumulated)))
                    else:
                        accumulated.extend(chunk_data)
                data = bytes(accumulated)
            except Exception as e:
                failed.append((name, str(e)))
                continue

            if len(data) != raw_size:
                failed.append((name, f'압축 해제 크기 불일치 ({len(data)} != {raw_size})'))
                continue

            new_crc = zlib.crc32(data) & 0xffffffff
            if new_crc != crc32 & 0xffffffff:
                failed.append((name, 'CRC 불일치 (파일이 손상되었을 수 있음)'))
                continue

            local_path = out_dir / name
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, 'wb') as out:
                out.write(data)
            written += 1

            if progress and (i + 1) % 50 == 0:
                progress(i + 1, total)

        if progress:
            progress(total, total)

        log(f"\n완료: {written} / {total}개 파일 작성됨")
        if failed:
            log(f"\n실패한 파일 {len(failed)}개:")
            for n, err in failed[:30]:
                log(f"  {n}: {err}")
            return False
        return True


class App:
    def __init__(self, root):
        self.root = root
        root.title("테일즈 오브 이노센스 R 한글패치 - L7C 압축 해제 도구")
        root.geometry("720x520")

        pad = dict(padx=10, pady=6)

        frm = ttk.Frame(root)
        frm.pack(fill="x", **pad)

        ttk.Label(frm, text="① 패치된 toidata_release.l7c 파일:").grid(row=0, column=0, sticky="w")
        self.l7c_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.l7c_var, width=70).grid(row=1, column=0, sticky="we")
        ttk.Button(frm, text="찾아보기...", command=self.pick_l7c).grid(row=1, column=1, padx=5)

        ttk.Label(frm, text="② 게임 설치 폴더 (예: ux0/app/PCSG00009):").grid(row=2, column=0, sticky="w", pady=(12, 0))
        self.out_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.out_var, width=70).grid(row=3, column=0, sticky="we")
        ttk.Button(frm, text="찾아보기...", command=self.pick_outdir).grid(row=3, column=1, padx=5)

        frm.columnconfigure(0, weight=1)

        self.start_btn = ttk.Button(root, text="③ 압축 해제 시작", command=self.start)
        self.start_btn.pack(pady=10)

        self.progress = ttk.Progressbar(root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0, 10))

        self.log_box = scrolledtext.ScrolledText(root, height=18, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log("안내: ①에서 xdelta로 패치한 toidata_release.l7c를, ②에서 게임이 "
                  "설치된 실제 폴더(eboot.bin이 있는 바로 그 폴더)를 선택한 뒤 "
                  "③ 버튼을 누르세요. 14,000여 개 파일을 처리하므로 몇 분 걸릴 수 있습니다.")

    def pick_l7c(self):
        path = filedialog.askopenfilename(
            title="패치된 toidata_release.l7c 선택",
            filetypes=[("L7C 파일", "*.l7c"), ("모든 파일", "*.*")])
        if path:
            self.l7c_var.set(path)
            if not self.out_var.get():
                self.out_var.set(str(Path(path).parent))

    def pick_outdir(self):
        path = filedialog.askdirectory(title="게임 설치 폴더 선택")
        if path:
            self.out_var.set(path)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_progress(self, current, total):
        self.progress["maximum"] = total
        self.progress["value"] = current

    def start(self):
        l7c = self.l7c_var.get().strip()
        outdir = self.out_var.get().strip()

        if not l7c or not Path(l7c).is_file():
            messagebox.showerror("오류", "toidata_release.l7c 파일을 올바르게 선택해주세요.")
            return
        if not outdir:
            messagebox.showerror("오류", "게임 설치 폴더를 선택해주세요.")
            return
        if not (Path(outdir) / "eboot.bin").exists():
            if not messagebox.askyesno(
                    "확인",
                    "선택하신 폴더에 eboot.bin이 없습니다. 게임 설치 폴더가 "
                    "맞는지 다시 확인해주세요.\n\n그래도 계속 진행할까요?"):
                return

        self.start_btn.configure(state="disabled")
        self.progress["value"] = 0

        thread = threading.Thread(target=self._run, args=(l7c, outdir), daemon=True)
        thread.start()

    def _run(self, l7c, outdir):
        try:
            ok = unpack(l7c, outdir, log=lambda m: self.root.after(0, self.log, m),
                        progress=lambda c, t: self.root.after(0, self.set_progress, c, t))
        except Exception:
            ok = False
            tb = traceback.format_exc()
            self.root.after(0, self.log, f"오류 발생:\n{tb}")

        def finish():
            self.start_btn.configure(state="normal")
            if ok:
                messagebox.showinfo("완료", "압축 해제가 완료됐습니다. 이제 게임을 실행해보세요.")
            else:
                messagebox.showwarning("일부 실패", "일부 파일 처리에 실패했습니다. 위 로그를 확인해주세요.")

        self.root.after(0, finish)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
