#!/usr/bin/env python3
# 子集字体抓取：扫 CWD 的 groups.full.json + chapters.json + widgets.json 全部字符，
# 从 Google Fonts css2 &text= 拉 4 款字体的最小子集 woff2 存 fonts/。可复用。
import json, pathlib, re, urllib.parse, urllib.request, sys, ssl

HERE = pathlib.Path('.')
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE  # macOS python.org 缺根证书的常见绕过

def collect():
    chars = set()
    def eat(x):
        if isinstance(x, str): chars.update(x)
        elif isinstance(x, list):
            for v in x: eat(v)
        elif isinstance(x, dict):
            for v in x.values(): eat(v)
    for fn in ("groups.full.json", "widgets.json"):
        p = HERE / fn
        if p.exists(): eat(json.loads(p.read_text(encoding="utf-8")))
    cj = HERE / "chapters.json"
    if cj.exists():
        for c in json.loads(cj.read_text(encoding="utf-8")).get("chapters", []):
            eat(c[2])
    # 静态 UI 串 + 基础 ASCII/标点/数字
    chars.update("原片实锤原话VS▶“”·…—,.!?:;%/+-<>()[]'\"&@#$ ")
    chars.update("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    chars.discard("\n"); chars.discard("\t")
    return "".join(sorted(chars))

FONTS = {
 "SC900":   ("Noto Sans SC",  "wght@900"),
 "SC500":   ("Noto Sans SC",  "wght@500"),
 "Serif700":("Noto Serif SC", "wght@700"),
 "Mono600": ("IBM Plex Mono", "wght@600"),
}

def fetch(name, family, axis, text):
    fam = family.replace(" ", "+")
    url = f"https://fonts.googleapis.com/css2?family={fam}:{axis}&text={urllib.parse.quote(text)}&display=swap"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    css = urllib.request.urlopen(req, timeout=30, context=SSL_CTX).read().decode()
    m = re.search(r"url\((https://[^)]+)\)", css)
    if not m:
        print(f"  !! {name}: no woff2 in css"); return False
    woff = urllib.request.urlopen(urllib.request.Request(m.group(1), headers={"User-Agent": UA}), timeout=30, context=SSL_CTX).read()
    out = HERE / "fonts" / f"{name}.woff2"
    out.parent.mkdir(exist_ok=True)
    out.write_bytes(woff)
    print(f"  {name}: {len(woff)} bytes")
    return True

if __name__ == "__main__":
    text = collect()
    print(f"chars: {len(text)}")
    ok = all(fetch(n, fam, ax, text) for n, (fam, ax) in FONTS.items())
    print("done" if ok else "FAILED")
    sys.exit(0 if ok else 1)
