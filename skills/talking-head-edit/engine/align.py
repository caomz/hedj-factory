#!/usr/bin/env python3
"""把 authored 字幕组按顺序对齐到 whisper 词级时间轴（difflib 模糊匹配，容忍错字/口误）。
用法: python3 align.py groups.authored.json groups.full.json"""
import json, re, sys, difflib, pathlib

HERE = pathlib.Path(".")  # 从项目 build/ 目录调用，读写当前目录
src = sys.argv[1] if len(sys.argv) > 1 else "groups.authored.json"
out = sys.argv[2] if len(sys.argv) > 2 else "groups.full.json"

# ---- 1) whisper 字符级时间轴 ----
d = json.load(open(HERE/"words.json"))
wchars, wstart, wend = [], [], []
for s in d["transcription"]:
    t = s["text"]; a = s["offsets"]["from"]/1000.0; b = s["offsets"]["to"]/1000.0
    n = max(len(t), 1)
    for i, ch in enumerate(t):
        wchars.append(ch); wstart.append(a+(b-a)*i/n); wend.append(a+(b-a)*(i+1)/n)
TOTAL = wend[-1]

def norm(s):
    # 保留中日韩 + 字母数字，转小写；去标点/空格
    return "".join(c.lower() for c in s if ('一'<=c<='鿿') or c.isalnum())

# whisper 规范化串 + 映射到原字符索引
W = []; Wmap = []
for i, ch in enumerate(wchars):
    nc = norm(ch)
    if nc:
        W.append(nc); Wmap.append(i)
W = "".join(W)

# ---- 2) authored 串 + 组边界 ----
groups = json.loads((HERE/src).read_text(encoding="utf-8"))
A = ""; bounds = []  # bounds[g] = (start_idx_in_A, end_idx_in_A)
for g in groups:
    a0 = len(A); A += norm(g["cn"]); bounds.append((a0, len(A)))

# ---- 3) difflib 对齐 A->W ----
sm = difflib.SequenceMatcher(None, A, W, autojunk=False)
a2w = [None]*(len(A)+1)
for ai, wi, size in sm.get_matching_blocks():
    for k in range(size):
        a2w[ai+k] = wi+k
# 用最近的已知锚点插值填补 None
known = [i for i in range(len(A)+1) if a2w[i] is not None]
def nearest(idx):
    # 二分找最近 known
    import bisect
    p = bisect.bisect_left(known, idx)
    cands = []
    if p < len(known): cands.append(known[p])
    if p > 0: cands.append(known[p-1])
    return min(cands, key=lambda k: abs(k-idx))
for i in range(len(A)+1):
    if a2w[i] is None:
        j = nearest(i); a2w[i] = a2w[j]

def t_start(a_idx):
    wi = a2w[a_idx]
    if wi is None or wi >= len(Wmap): return TOTAL
    return wstart[Wmap[min(wi, len(Wmap)-1)]]
def t_end(a_idx):  # a_idx 为该组最后一个字符的位置
    wi = a2w[a_idx]
    if wi is None or wi >= len(Wmap): return TOTAL
    return wend[Wmap[min(wi, len(Wmap)-1)]]

# ---- 4) 赋时间 + 单调化 ----
res = []
prev_end = 0.0
for gi, g in enumerate(groups):
    s, e = bounds[gi]
    st = t_start(s)
    en = t_end(e-1) if e > s else st+0.6
    st = max(st, prev_end)            # 不回退
    if en <= st: en = st+0.6
    res.append({**g, "start": round(st,2), "end": round(en,2)})
    prev_end = en

# 防重叠：当前 end 不超过下一组 start
for i in range(len(res)-1):
    if res[i]["end"] > res[i+1]["start"]:
        res[i]["end"] = max(res[i]["start"]+0.4, round(res[i+1]["start"]-0.02,2))
# 末组兜底
res[-1]["end"] = min(res[-1]["end"], round(TOTAL,2))

pathlib.Path(HERE/out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
# 体检
gaps = sum(1 for i in range(len(res)-1) if res[i+1]["start"]-res[i]["end"]>1.5)
print(f"对齐 {len(res)} 组 → {out}")
print(f"总时长 {TOTAL:.1f}s, 首组 {res[0]['start']}s, 末组 {res[-1]['end']}s, >1.5s 空档 {gaps} 处")
print("前5组:")
for r in res[:5]: print(f"  {r['start']:6.2f}-{r['end']:6.2f}  {r['cn']}")
print("后3组:")
for r in res[-3:]: print(f"  {r['start']:6.2f}-{r['end']:6.2f}  {r['cn']}")
