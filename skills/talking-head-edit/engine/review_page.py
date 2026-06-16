#!/usr/bin/env python3
# 设计系统 / 素材审阅页：把本片的主题色 + 全部素材 + 全部卡片(静态渲染) + 字幕样例
# 摆成一张 review.html，渲染前先让用户审。复用 index.html 里已生成好的卡片(主题已套)。
# 用法：在本片 build/ 里，先 build_caps.py 生成 index.html，再跑
#   python3 ~/.claude/skills/talking-head-edit/engine/review_page.py
#   (脚本读当前目录 CWD;装好后引擎在 ~/.claude/skills/talking-head-edit/engine/)
import re, json, pathlib, base64
HERE = pathlib.Path('.')
idx = (HERE / "index.html").read_text(encoding="utf-8")

style = re.search(r"<style>(.*?)</style>", idx, re.S).group(1)
wg_lines = re.findall(r'<div class="wg" id="wg-\d+">.*?</div></div>', idx)
# caption samples: 取前几个 A 和一个 B
cg_lines = re.findall(r'<div class="cg[^"]*" id="cg-\d+">.*?</div></div>', idx)

W = json.loads((HERE / "widgets.json").read_text(encoding="utf-8")) if (HERE/"widgets.json").exists() else []
T = json.loads((HERE / "theme.json").read_text(encoding="utf-8")) if (HERE/"theme.json").exists() else {}

def label(i):
    if i < len(W):
        w = W[i]; k = w.get("kind", "?")
        return f"{k} · {w.get('start','?')}–{w.get('end','?')}s"
    return f"widget {i}"

# 主题色板
swatch_keys = [("accent","强调"),("bone","主文字"),("bone_bright","B 档"),("en","英文"),
               ("graphite","副文字"),("graphite2","卡片标签"),("ink","卡底"),("dim","未播")]
swatches = "".join(
    f'<div class="sw"><div class="chip" style="background:{T.get(k,"#888")}"></div>'
    f'<div class="swlab">{lab}<br><code>{T.get(k,"(默认)")}</code></div></div>'
    for k,lab in swatch_keys)

# 素材库
news = HERE / "news"
assets = ""
if news.exists():
    for p in sorted(news.iterdir()):
        if p.suffix.lower() in (".png",".jpg",".jpeg",".webp"):
            b = base64.b64encode(p.read_bytes()).decode()
            ext = p.suffix.lstrip(".").replace("jpg","jpeg")
            assets += f'<div class="asset"><img src="data:image/{ext};base64,{b}"><div class="alab">{p.name}</div></div>'
naval = HERE / "naval"
clips = ""
if naval.exists():
    for p in sorted(naval.glob("*.mp4")):
        clips += f'<div class="alab">🎬 {p.name}</div>'

# 卡片：原生尺寸(968px)，单列，逐张标注。最高保真，任何浏览器都稳。
cards = "".join(
    f'<div class="tile"><div class="tlab">{label(i)}</div>'
    f'<div class="cardbox">{w}</div></div>'
    for i, w in enumerate(wg_lines))

out = f"""<!doctype html><html><head><meta charset="utf-8"><style>
{style}
/* —— review 覆盖：让卡片/字幕静态可见 —— */
body{{margin:0;background:#0c0b0a;color:#eee;font-family:-apple-system,sans-serif;padding:48px 56px}}
h2{{font-size:30px;margin:48px 0 20px;color:{T.get('accent','#E9B949')};letter-spacing:.02em}}
h2:first-child{{margin-top:0}}
.row{{display:flex;flex-wrap:wrap;gap:18px}}
.sw{{display:flex;align-items:center;gap:12px;width:230px}}
.chip{{width:46px;height:46px;border-radius:10px;border:1px solid rgba(255,255,255,.15);flex:none}}
.swlab{{font-size:14px;color:#bbb}} .swlab code{{color:#888;font-size:12px}}
.asset img{{width:280px;border-radius:8px;display:block;border:1px solid rgba(255,255,255,.12);background:#fff}}
.alab{{font-size:13px;color:#aaa;margin-top:6px;font-family:monospace}}
.grid{{display:flex;flex-direction:column;gap:34px;max-width:1000px}}
.tile{{}}
.tlab{{font:600 16px/1 monospace;color:{T.get('accent','#E9B949')};margin-bottom:12px;letter-spacing:.04em}}
.cardbox{{width:1000px;padding:16px;border-radius:16px;
  background:radial-gradient(circle at 50% 30%,#2a2622,#100e0c)}}
.cardbox .wg{{position:static!important;left:auto!important;right:auto!important;top:auto!important;
  opacity:1!important;visibility:visible!important;transform:none!important;width:968px}}
.cardbox .clipvid{{background:#222;min-height:300px}}
.capwrap{{width:1000px;margin-bottom:20px;padding:30px 0;overflow:hidden;border-radius:16px;
  background:radial-gradient(circle at 50% 40%,#2a2622,#0f0d0b)}}
.capbox .cg{{position:static!important;left:auto!important;right:auto!important;bottom:auto!important;
  opacity:1!important;visibility:visible!important;transform:none!important;padding:0 60px}}
.note{{color:#999;font-size:14px;margin:6px 0 0}}
</style></head><body>
<h2>主题配色 · {T.get('_note','默认琥珀')}</h2>
<div class="row">{swatches}</div>
<h2>素材库 news/ + 剪入片段 naval/</h2>
<div class="row">{assets}</div><div class="row" style="margin-top:10px">{clips}</div>
<p class="note">检查：素材是否权威/清晰、是否对得上要讲的点、有没有水印/版权问题。</p>
<h2>卡片 widgets（{len(wg_lines)} 张，按出现顺序）</h2>
<div class="grid">{cards}</div>
<p class="note">检查：每张卡的文字/数字对不对、上没上对主题色、时间点对不对、左右居中对不对。</p>
<h2>字幕样例（A 档 / B 档）</h2>
<div class="row">{''.join(f'<div class="capwrap"><div class="capbox">{c}</div></div>' for c in cg_lines[:6])}</div>
<p class="note">检查：中文逐字贴录音(对照 groups.raw.json)、英译地道、描金是不是只在关键词。</p>
</body></html>"""
(HERE / "review.html").write_text(out, encoding="utf-8")
print(f"wrote review.html — {len(wg_lines)} cards + {len(swatch_keys)} swatches + assets. open it to review.")
