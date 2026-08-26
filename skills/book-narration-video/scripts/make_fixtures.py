#!/usr/bin/env python3
# make_fixtures.py — 生成微型合成书源（txt/epub/pdf），默认写到给定目录。
# 全部本地合成、无版权内容；测试请写到临时目录，不要覆盖仓库内已跟踪文件。
import argparse
import zipfile
from pathlib import Path


def make_txt(fix: Path):
    (fix / "sample.txt").write_text(
        "微型习惯手册（合成测试书，无版权内容）\n"
        "作者：测试员\n"
        "\n"
        "第一章 微小的开始\n"
        "\n"
        "改变不是靠意志力硬扛，而是把动作缩到小得不可能失败。\n"
        "每天做一个俯卧撑，胜过计划一百个却一次没做。\n"
        "\n"
        "第二章 环境的杠杆\n"
        "\n"
        "把水果放在桌上，把手机放进抽屉——环境替你做了大半决定。\n"
        "金句：你不是缺自律，你是缺一个顺手的环境。\n"
        "\n"
        "第三章 身份的复利\n"
        "\n"
        "每次微小的行动，都是给「我是这样的人」投一票。\n"
        "票数够了，习惯就不再需要坚持。\n",
        encoding="utf-8")


def make_epub(fix: Path):
    mimetype = "application/epub+zip"
    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""
    opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:00000000-0000-0000-0000-000000000001</dc:identifier>
    <dc:title>微型习惯手册</dc:title>
    <dc:creator>测试员</dc:creator>
    <dc:language>zh</dc:language>
  </metadata>
  <manifest>
    <item id="ch1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
    <item id="ch3" href="ch3.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="ch1"/><itemref idref="ch2"/><itemref idref="ch3"/></spine>
</package>"""

    def xhtml(title, paras):
        body = "\n".join(f"    <p>{p}</p>" for p in paras)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>{title}</title></head>
  <body>
    <h1>{title}</h1>
{body}
  </body>
</html>"""

    chapters = {
        "OEBPS/ch1.xhtml": xhtml("第一章 微小的开始", [
            "改变不是靠意志力硬扛，而是把动作缩到小得不可能失败。",
            "每天做一个俯卧撑，胜过计划一百个却一次没做。"]),
        "OEBPS/ch2.xhtml": xhtml("第二章 环境的杠杆", [
            "把水果放在桌上，把手机放进抽屉——环境替你做了大半决定。",
            "金句：你不是缺自律，你是缺一个顺手的环境。"]),
        "OEBPS/ch3.xhtml": xhtml("第三章 身份的复利", [
            "每次微小的行动，都是给「我是这样的人」投一票。",
            "票数够了，习惯就不再需要坚持。"]),
    }
    with zipfile.ZipFile(fix / "sample.epub", "w") as zf:
        zf.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.opf", opf)
        for name, content in chapters.items():
            zf.writestr(name, content)


def make_pdf(fix: Path):
    # 手搓最小两页 pdf（无压缩流 + 正确 xref）。PDF xref 行尾空格是规范要求。
    def page_stream(lines):
        ops = ["BT", "/F1 12 Tf", "72 720 Td", "14 TL"]
        for k, line in enumerate(lines):
            if k:
                ops.append("T*")
            ops.append(f"({line}) Tj")
        ops.append("ET")
        return "\n".join(ops).encode("ascii")

    s1 = page_stream(["Tiny Habits Field Notes (synthetic test book).",
                      "Chapter one: shrink the action until failure is impossible."])
    s2 = page_stream(["Page two marker: environment beats willpower.",
                      "Identity compounds one small vote at a time."])

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
           b"/Resources << /Font << /F1 7 0 R >> >> /Contents 5 0 R >>",
        4: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
           b"/Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>",
        5: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(s1), s1),
        6: b"<< /Length %d >>\nstream\n%s\nendstream" % (len(s2), s2),
        7: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num in sorted(objs):
        offsets[num] = len(out)
        out += b"%d 0 obj\n%s\nendobj\n" % (num, objs[num])
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objs) + 1)
    out += b"0000000000 65535 f \n"
    for num in sorted(objs):
        out += b"%010d 00000 n \n" % offsets[num]
    out += (b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objs) + 1, xref_pos))
    (fix / "sample.pdf").write_bytes(bytes(out))


def make_all(fix: Path):
    fix.mkdir(parents=True, exist_ok=True)
    make_txt(fix)
    make_epub(fix)
    make_pdf(fix)
    return sorted(fix.iterdir())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="生成合成书源 fixtures 到指定目录")
    ap.add_argument("--out", type=Path, required=True,
                    help="输出目录（测试请用临时目录，勿写回仓库 fixtures/）")
    args = ap.parse_args()
    for f in make_all(args.out):
        print(f"✓ {f} ({f.stat().st_size} B)")
