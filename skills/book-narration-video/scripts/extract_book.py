#!/usr/bin/env python3
# extract_book.py — 书源提取：epub / pdf / txt / md → 干净纯文本 + source.txt 元数据
# 配合 book-narration-video Phase 0：先 --list 看目录，再按章节/页码范围提取，别一次性塞全书进上下文。
#
# 用法：
#   python3 extract_book.py <书源文件> --list                                # 只列章节/页数，不写文件
#   python3 extract_book.py 书.epub --out 案例库/<book-slug>/ --chapters 2-5  # epub/txt/md 按章提取
#   python3 extract_book.py 书.pdf  --out 案例库/<book-slug>/ --pages 10-25   # pdf 按页提取
#   python3 extract_book.py 书.txt                                           # 不给 --out 就打到 stdout
#
# 选项：
#   --out DIR         输出目录（推荐 案例库/<book-slug>/），产出 原文.txt + 建/更新 source.txt
#   --chapters SPEC   章节范围，1-based：`2-5` / `1,3,7-9` / `3-`（epub/txt/md；先 --list 看编号）
#   --pages SPEC      页码范围（仅 pdf），格式同上
#   --max-chars N     最多提取字符数，默认 60000，0=不限（超了就截断并标注）
#   --title/--author  书名/作者（写进 source.txt；epub 能自动读元数据，txt/pdf 建议手动给）
#   --name FILE       输出文本文件名，默认 原文.txt
#
# 设计要点：
# - 零必装依赖：epub 用 zipfile+xml（stdlib）；pdf 优先 `pdftotext`（poppler），
#   没有则试 pypdf（可选装），再不行用内置纯 Python 兜底（简单 pdf 可用；扫描版/CID
#   中文字体请装 poppler：`brew install poppler` / `apt install poppler-utils`）。
# - 版权纪律：只提取要讲的范围；source.txt 记清书名/作者/来源/讲书范围。
import argparse
import hashlib
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import zipfile
import zlib
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

DEFAULT_MAX_CHARS = 60000
SEP = "═" * 8


# ---------- 通用 ----------

def die(msg: str, code: int = 1):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(code)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_outfile(outdir: Path, name: str) -> Path:
    """Resolve output file under outdir; reject absolute paths and .. escape."""
    outdir = outdir.resolve()
    candidate = Path(name)
    if candidate.is_absolute():
        die(f"--name 不能是绝对路径：{name!r}")
    if ".." in candidate.parts:
        die(f"--name 不允许包含 '..'：{name!r}")
    outfile = (outdir / candidate).resolve()
    try:
        outfile.relative_to(outdir)
    except ValueError:
        die(f"--name 逃出了 --out 目录：{name!r} → {outfile}")
    return outfile


def atomic_write_text(path: Path, text: str):
    """Write via temp file in same directory, then os.replace (atomic on same FS)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def detect_format(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".epub":
        return "epub"
    if ext == ".pdf":
        return "pdf"
    if ext in (".txt", ".md", ".markdown", ".text"):
        return "text"
    head = path.open("rb").read(8)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK\x03\x04") and zipfile.is_zipfile(path):
        return "epub"
    return "text"


def parse_range(spec: str, total: int) -> list:
    """`2-5` / `1,3,7-9` / `3-` / `-4` → 排好序的 1-based 序号列表。"""
    picked = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                lo = int(a) if a.strip() else 1
                hi = int(b) if b.strip() else total
            except ValueError:
                die(f"范围写法不对：{part!r}（示例：2-5 / 1,3,7-9 / 3-）")
        else:
            try:
                lo = hi = int(part)
            except ValueError:
                die(f"范围写法不对：{part!r}（示例：2-5 / 1,3,7-9 / 3-）")
        picked.update(range(max(1, lo), min(total, hi) + 1))
    if not picked:
        die(f"范围 {spec!r} 没选中任何内容（共 {total} 个可选）")
    return sorted(picked)


def decode_text(raw: bytes) -> str:
    for enc in ("utf-8-sig", "gb18030", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw.decode("utf-8", "replace")


def tidy(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ---------- epub（zipfile + xml + html.parser，全 stdlib）----------

class _HTMLText(HTMLParser):
    BLOCK = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br",
             "hr", "section", "article", "blockquote", "ul", "ol", "table",
             "figcaption", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self.heading = [], "", ""
        self._skip = 0
        self._cap, self._buf = None, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "title" and not self.title:
            self._cap, self._buf = "title", []
        elif tag in ("h1", "h2", "h3") and not self.heading:
            self._cap, self._buf = "heading", []

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")
        if self._cap == "title" and tag == "title":
            self.title = "".join(self._buf).strip()
            self._cap = None
        elif self._cap == "heading" and tag in ("h1", "h2", "h3"):
            self.heading = "".join(self._buf).strip()
            self._cap = None

    def handle_data(self, data):
        if self._skip:
            return
        if self._cap == "title":
            self._buf.append(data)
            return
        if self._cap == "heading":
            self._buf.append(data)
        self.parts.append(data)


def html_to_text(html: str):
    p = _HTMLText()
    try:
        p.feed(html)
        p.close()
    except Exception:
        pass
    return tidy("".join(p.parts)), (p.heading or p.title)


def load_epub(path: Path) -> dict:
    """→ {title, author, chapters: [{title, text}]}，章节按 spine 顺序。"""
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        die(f"不是合法 epub（zip 打不开）：{path}")
    try:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = container.find(".//{*}rootfile").get("full-path")
        opf = ET.fromstring(zf.read(opf_path))
    except Exception as e:
        die(f"epub 结构解析失败（container/opf）：{e}")
    opf_dir = posixpath.dirname(opf_path)

    def meta(tag):
        el = opf.find(f".//{{http://purl.org/dc/elements/1.1/}}{tag}")
        return (el.text or "").strip() if el is not None and el.text else ""

    manifest = {}
    for item in opf.findall(".//{*}manifest/{*}item"):
        manifest[item.get("id")] = (item.get("href", ""), item.get("media-type", ""))

    names = set(zf.namelist())
    chapters = []
    for ref in opf.findall(".//{*}spine/{*}itemref"):
        href, mtype = manifest.get(ref.get("idref"), ("", ""))
        if not href or ("html" not in mtype and not href.endswith((".xhtml", ".html", ".htm"))):
            continue
        full = posixpath.normpath(posixpath.join(opf_dir, unquote(href)))
        if full not in names:
            continue
        text, heading = html_to_text(decode_text(zf.read(full)))
        if not text:
            continue
        chapters.append({"title": heading or posixpath.basename(full), "text": text})
    if not chapters:
        die("epub 里没解析出正文章节（spine 为空或全是图片页）")
    return {"title": meta("title"), "author": meta("creator"), "chapters": chapters}


# ---------- txt / md ----------

_CHAPTER_RE = re.compile(
    r"^\s*(?:"
    r"#{1,3}\s+\S.*"                                            # markdown 标题
    r"|第\s*[0-9一二三四五六七八九十百千零两〇]+\s*[章回节卷部篇讲].*"  # 中文章节
    r"|(?:Chapter|CHAPTER|Part|PART)\s+[\w一-九]+.*"              # 英文章节
    r")\s*$")


def load_textfile(path: Path) -> dict:
    lines = decode_text(path.read_bytes()).replace("\r\n", "\n").split("\n")
    chapters, cur_title, cur = [], "（卷首）", []

    def flush():
        text = tidy("\n".join(cur))
        if text:
            chapters.append({"title": cur_title, "text": text})

    for line in lines:
        if _CHAPTER_RE.match(line):
            flush()
            cur_title, cur = line.strip().lstrip("#").strip(), [line]
        else:
            cur.append(line)
    flush()
    if not chapters:
        die(f"文件是空的：{path}")
    return {"title": "", "author": "", "chapters": chapters}


# ---------- pdf：pdftotext → pypdf（可选装）→ 纯 stdlib 兜底 ----------

def _pdf_objects(data: bytes) -> dict:
    objs = {}
    for m in re.finditer(rb"(\d+)\s+\d+\s+obj\b", data):
        end = data.find(b"endobj", m.end())
        if end == -1:
            continue
        s = data.find(b"stream", m.end())
        if s != -1 and s < end:  # endobj 出现在二进制流里：跳到 endstream 之后再找
            es = data.find(b"endstream", s)
            if es != -1:
                end = data.find(b"endobj", es)
                if end == -1:
                    continue
        objs.setdefault(int(m.group(1)), data[m.end():end])
    return objs


def _pdf_page_nums(data: bytes, objs: dict) -> list:
    """按页面树顺序返回 page 对象号；找不到 Root 就退化为文件顺序。"""
    pages, seen = [], set()

    def walk(num):
        body = objs.get(num)
        if body is None or num in seen:
            return
        seen.add(num)
        kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
        if kids:
            for km in re.finditer(rb"(\d+)\s+\d+\s+R", kids.group(1)):
                walk(int(km.group(1)))
        elif re.search(rb"/Type\s*/Page\b", body):
            pages.append(num)

    root = re.search(rb"/Root\s+(\d+)\s+\d+\s+R", data)
    if root:
        cat = objs.get(int(root.group(1)), b"")
        top = re.search(rb"/Pages\s+(\d+)\s+\d+\s+R", cat)
        if top:
            walk(int(top.group(1)))
    if not pages:
        pages = [n for n, b in sorted(objs.items()) if re.search(rb"/Type\s*/Page\b", b)]
    return pages


def _stream_data(body: bytes) -> bytes:
    i = body.find(b"stream")
    if i == -1:
        return b""
    head = body[:i]
    j = i + 6
    if body[j:j + 2] == b"\r\n":
        j += 2
    elif body[j:j + 1] == b"\n":
        j += 1
    raw = body[j:body.rfind(b"endstream")]
    if re.search(rb"/Filter\s*(?:\[\s*)?/FlateDecode", head):
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return b""
    if b"/Filter" in head:
        return b""  # 其它压缩滤镜不支持，交给 pdftotext/pypdf
    return raw


def _lit_string(cs: bytes, i: int):
    i += 1
    depth, out = 1, bytearray()
    esc = {0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12, 0x28: 40, 0x29: 41, 0x5C: 0x5C}
    while i < len(cs) and depth:
        c = cs[i]
        if c == 0x5C:  # backslash
            i += 1
            if i >= len(cs):
                break
            e = cs[i]
            if e in esc:
                out.append(esc[e])
                i += 1
            elif 0x30 <= e <= 0x37:  # 八进制转义，最多 3 位
                digits = ""
                while i < len(cs) and len(digits) < 3 and 0x30 <= cs[i] <= 0x37:
                    digits += chr(cs[i])
                    i += 1
                out.append(int(digits, 8) & 0xFF)
            elif e in (10, 13):  # 续行
                i += 1
                if e == 13 and cs[i:i + 1] == b"\n":
                    i += 1
            else:
                out.append(e)
                i += 1
        elif c == 0x28:
            depth += 1
            out.append(c)
            i += 1
        elif c == 0x29:
            depth -= 1
            if depth:
                out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    return bytes(out), i


def _pdf_str(b: bytes) -> str:
    if b[:2] == b"\xfe\xff":
        return b[2:].decode("utf-16-be", "replace")
    return b.decode("latin-1", "replace")


def _content_text(cs: bytes) -> str:
    out, pend = [], []
    i, n = 0, len(cs)
    op_re = re.compile(rb"[A-Za-z'\"*]+")
    while i < n:
        c = cs[i:i + 1]
        if c == b"(":
            s, i = _lit_string(cs, i)
            pend.append(_pdf_str(s))
        elif c == b"<" and cs[i + 1:i + 2] != b"<":
            j = cs.find(b">", i)
            if j == -1:
                break
            hx = re.sub(rb"\s", b"", cs[i + 1:j])
            if len(hx) % 2:
                hx += b"0"
            try:
                pend.append(_pdf_str(bytes.fromhex(hx.decode("ascii"))))
            except ValueError:
                pass
            i = j + 1
        elif c == b"<":
            i += 2
        elif c.isalpha() or c in (b"'", b'"', b"*"):
            m = op_re.match(cs, i)
            op = m.group(0)
            i = m.end()
            if op in (b"Tj", b"TJ"):
                out.extend(pend)
            elif op in (b"'", b'"'):
                out.append("\n")
                out.extend(pend)
            elif op in (b"Td", b"TD", b"T*", b"ET"):
                out.append("\n")
            pend = []
        else:
            i += 1
    return "".join(out)


def pdf_extract_stdlib(path: Path) -> list:
    """纯 stdlib 兜底：→ 每页一段文本的列表。只支持无压缩/Flate 的简单 pdf。"""
    data = path.read_bytes()
    objs = _pdf_objects(data)
    pages = []
    for num in _pdf_page_nums(data, objs):
        body = objs[num]
        m = re.search(rb"/Contents\s+(\d+)\s+\d+\s+R", body)
        if m:
            nums = [int(m.group(1))]
        else:
            arr = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
            nums = [int(x.group(1)) for x in re.finditer(rb"(\d+)\s+\d+\s+R", arr.group(1))] if arr else []
        cs = b"".join(_stream_data(objs.get(nn, b"")) for nn in nums)
        pages.append(tidy(_content_text(cs)))
    return pages


def pdf_page_count(path: Path) -> int:
    try:
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, timeout=60)
        m = re.search(r"^Pages:\s+(\d+)", out.stdout, re.M)
        if m:
            return int(m.group(1))
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    try:
        import pypdf
        return len(pypdf.PdfReader(str(path)).pages)
    except ImportError:
        pass
    data = path.read_bytes()
    return len(_pdf_page_nums(data, _pdf_objects(data)))


def load_pdf(path: Path, page_range) -> dict:
    """→ {title, author, chapters: [{title:'第N页', text}]}；page_range 为 1-based 页码列表或 None。"""
    total = pdf_page_count(path)
    if total <= 0:
        die(f"读不出 pdf 页数：{path}")
    wanted = page_range or list(range(1, total + 1))

    def wrap(pages_texts):  # [(页码, 文本)]
        chs = [{"title": f"第 {p} 页", "text": t} for p, t in pages_texts if t.strip()]
        if not chs:
            die("选中的页提取不出文字（可能是扫描版 pdf——需要 OCR，超出本脚本范围）")
        return {"title": "", "author": "", "chapters": chs, "total_pages": total}

    # 首选 pdftotext（poppler）
    try:
        texts = []
        for p in wanted:
            out = subprocess.run(
                ["pdftotext", "-q", "-enc", "UTF-8", "-f", str(p), "-l", str(p), str(path), "-"],
                capture_output=True, timeout=300, check=True)
            texts.append((p, tidy(out.stdout.decode("utf-8", "replace"))))
        return wrap(texts)
    except FileNotFoundError:
        pass
    except subprocess.SubprocessError as e:
        print(f"⚠️  pdftotext 失败（{e}），换备用方案", file=sys.stderr)

    # 备选 pypdf（可选装，不强求）
    try:
        import pypdf
        reader = pypdf.PdfReader(str(path))
        return wrap([(p, tidy(reader.pages[p - 1].extract_text() or "")) for p in wanted
                     if p <= len(reader.pages)])
    except ImportError:
        pass
    except Exception as e:
        print(f"⚠️  pypdf 失败（{e}），换纯 stdlib 兜底", file=sys.stderr)

    # 兜底：纯 stdlib（简单 pdf 可用）
    print("⚠️  没装 pdftotext（poppler），用内置纯 Python 兜底提取——简单 pdf 可用；"
          "复杂排版/中文 CID 字体建议 `brew install poppler` 或 `apt install poppler-utils`",
          file=sys.stderr)
    all_pages = pdf_extract_stdlib(path)
    return wrap([(p, all_pages[p - 1]) for p in wanted if p <= len(all_pages)])


# ---------- 输出 ----------

def list_book(book: dict, fmt: str):
    if fmt == "pdf":
        print(f"📄 pdf 共 {book['total_pages']} 页。用 --pages 选页提取，如 --pages 10-25")
        return
    print(f"📖 {book['title'] or '（书名未知）'}"
          + (f" — {book['author']}" if book["author"] else "")
          + f" · 共 {len(book['chapters'])} 个章节段：")
    for i, ch in enumerate(book["chapters"], 1):
        title = re.sub(r"\s+", " ", ch["title"])[:40]
        print(f"  {i:>3}. {title}  (~{len(ch['text'])} 字)")
    print("\n用 --chapters 选段提取，如 --chapters 2-5（编号见上表）")


def assemble(book: dict, picked: list, meta: dict, max_chars: int):
    head = [f"# 《{meta['title']}》" + (f" — {meta['author']}" if meta["author"] else ""),
            f"# 来源：{meta['src']} · 提取范围：{meta['range']} · {meta['stamp']}",
            "# 由 extract_book.py 生成，喂给讲书拆解用；引用金句请核对原书。", ""]
    body_parts, used, truncated = [], 0, False
    for idx in picked:
        ch = book["chapters"][idx - 1]
        block = f"{SEP} {idx}. {ch['title']} {SEP}\n\n{ch['text']}"
        if max_chars and used + len(block) > max_chars:
            room = max_chars - used
            if room > 200:
                cut = block[:room]
                nl = cut.rfind("\n")
                if nl > room // 2:
                    cut = cut[:nl]
                body_parts.append(cut)
            truncated = True
            break
        body_parts.append(block)
        used += len(block) + 2
    body = "\n\n".join(body_parts)
    if truncated:
        body += (f"\n\n[已截断：达到 --max-chars {max_chars} 上限。"
                 f"要更多内容请缩小范围分次提取，或调大 --max-chars]")
        print(f"⚠️  超过 {max_chars} 字已截断（--max-chars 0 可不限，但别把整本书塞进上下文）",
              file=sys.stderr)
    return "\n".join(head) + "\n" + body + "\n", truncated


def update_source_txt(outdir: Path, meta: dict, dry_run: bool = False):
    p = outdir / "source.txt"
    record = (f"{meta['stamp']} · extract_book.py · {meta['src']}（{meta['fmt']}）"
              f" · sha256={meta['sha256'][:16]}…"
              f" · 范围：{meta['range']} · {meta['chars']} 字 → {meta['outname']}")
    if not p.exists():
        content = (
            f"书名：{meta['title']}\n"
            f"作者：{meta['author'] or '（待补）'}\n"
            f"ISBN：（待补）\n"
            f"素材来源：{meta['src']}（{meta['fmt']}，用户提供）\n"
            f"来源SHA256：{meta['sha256']}\n"
            f"讲书范围：{meta['range']}\n"
            f"\n--- 提取记录 ---\n{record}\n"
        )
        if dry_run:
            return "将创建（dry-run）"
        atomic_write_text(p, content)
        return "已创建"
    cur = p.read_text(encoding="utf-8")
    if "来源SHA256：" not in cur and "--- 提取记录 ---" in cur:
        # 旧文件补一行哈希（插在讲书范围后 / 提取记录前）
        cur = cur.replace("--- 提取记录 ---",
                          f"来源SHA256：{meta['sha256']}\n\n--- 提取记录 ---", 1)
    elif "来源SHA256：" not in cur:
        cur = cur.rstrip("\n") + f"\n来源SHA256：{meta['sha256']}\n"
    if "--- 提取记录 ---" not in cur:
        cur = cur.rstrip("\n") + "\n\n--- 提取记录 ---\n"
    elif not cur.endswith("\n"):
        cur += "\n"
    if dry_run:
        return "将追加提取记录（dry-run）"
    atomic_write_text(p, cur + record + "\n")
    return "已追加提取记录"


def main():
    ap = argparse.ArgumentParser(
        prog="extract_book.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="书源提取：epub / pdf / txt / md → 干净纯文本 + source.txt 元数据。\n"
                    "配合 book-narration-video Phase 0：先 --list 看目录，再按范围提取。",
        epilog="示例：\n"
               "  python3 extract_book.py 书.epub --list\n"
               "  python3 extract_book.py 书.epub --out 案例库/atomic-habits/ --chapters 2-5\n"
               "  python3 extract_book.py 书.pdf  --out 案例库/atomic-habits/ --pages 10-25\n"
               "  python3 extract_book.py 笔记.md --chapters 1,3    # 无 --out 则打到 stdout")
    ap.add_argument("source", help="书源文件（.epub / .pdf / .txt / .md）")
    ap.add_argument("--out", help="输出目录，推荐 案例库/<book-slug>/")
    ap.add_argument("--chapters", help="章节范围（epub/txt/md），如 2-5 / 1,3,7-9 / 3-")
    ap.add_argument("--pages", help="页码范围（仅 pdf），格式同 --chapters")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help=f"最多提取字符数，默认 {DEFAULT_MAX_CHARS}，0=不限")
    ap.add_argument("--title", default="", help="书名（写进 source.txt）")
    ap.add_argument("--author", default="", help="作者（写进 source.txt）")
    ap.add_argument("--name", default="原文.txt",
                    help="输出文本文件名（默认 原文.txt；禁止绝对路径与 '..'）")
    ap.add_argument("--list", action="store_true", help="只列章节/页数，不提取")
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印将写入的路径与字数，不落盘")
    ap.add_argument("--force", action="store_true",
                    help="允许覆盖已存在的输出文件（默认拒绝覆盖；覆盖前先 .bak）")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        die(f"找不到书源文件：{src}")
    fmt = detect_format(src)
    digest = sha256_file(src)

    if fmt == "pdf":
        if args.chapters:
            die("pdf 请用 --pages 选页（--chapters 只用于 epub/txt/md）")
        if args.list:
            list_book({"total_pages": pdf_page_count(src)}, fmt)
            return
        page_range = parse_range(args.pages, pdf_page_count(src)) if args.pages else None
        book = load_pdf(src, page_range)
        picked = list(range(1, len(book["chapters"]) + 1))
        range_label = f"第 {args.pages} 页" if args.pages else "全书（未指定 --pages）"
    else:
        if args.pages:
            die("--pages 只用于 pdf（epub/txt/md 用 --chapters）")
        book = load_epub(src) if fmt == "epub" else load_textfile(src)
        if args.list:
            list_book(book, fmt)
            return
        total = len(book["chapters"])
        picked = parse_range(args.chapters, total) if args.chapters else list(range(1, total + 1))
        range_label = f"章节段 {args.chapters}" if args.chapters else "全书（未指定 --chapters）"

    meta = {
        "title": args.title or book.get("title") or src.stem,
        "author": args.author or book.get("author", ""),
        "src": src.name, "fmt": fmt, "range": range_label,
        "stamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "outname": args.name,
        "sha256": digest,
    }
    text, _ = assemble(book, picked, meta, max(0, args.max_chars))
    meta["chars"] = len(text)

    if not args.out:
        if args.dry_run:
            print(f"[dry-run] 将打印到 stdout（{meta['chars']} 字，sha256={digest[:16]}…）")
            return
        print(text)
        return

    outdir = Path(args.out).expanduser().resolve()
    outfile = safe_outfile(outdir, args.name)

    if outfile.exists() and not args.force:
        die(f"输出已存在：{outfile}\n"
            f"   不想覆盖就换 --name；确认覆盖请加 --force（会先备份为 .bak）")

    if args.dry_run:
        print(f"[dry-run] 将写入：{outfile}（{meta['chars']} 字，{meta['range']}）")
        print(f"[dry-run] 来源 sha256={digest}")
        print(f"[dry-run] source.txt：{outdir / 'source.txt'}")
        return

    outdir.mkdir(parents=True, exist_ok=True)
    if outfile.exists() and args.force:
        bak = outfile.with_suffix(outfile.suffix + ".bak")
        # 备份也必须仍在 outdir 内
        bak = safe_outfile(outdir, bak.name)
        os.replace(outfile, bak)
        print(f"⚠️  已存在，备份为 {bak.name}", file=sys.stderr)

    atomic_write_text(outfile, text)
    action = update_source_txt(outdir, meta, dry_run=False)
    print(f"✅ 提取完成：{outfile}（{meta['chars']} 字，{meta['range']}）")
    print(f"   来源 sha256={digest}")
    print(f"   source.txt {action}：{outdir / 'source.txt'}（书名/作者/ISBN 留了待补位，记得核对）")


if __name__ == "__main__":
    main()
