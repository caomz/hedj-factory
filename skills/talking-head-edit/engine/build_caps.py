#!/usr/bin/env python3
# hyperframes 合成：视频 + 中英双语字幕(A/B) + widget 卡片(C) + 底部章节进度条
import base64, json, pathlib, html, sys
HERE=pathlib.Path('.')
def b64(p): return base64.b64encode((HERE/p).read_bytes()).decode()
def img64(p):
    ext=pathlib.Path(p).suffix.lstrip('.').replace('jpg','jpeg')
    return f"data:image/{ext};base64,"+base64.b64encode((HERE/'news'/p).read_bytes()).decode()

FONTS={"SC":("fonts/SC900.woff2",900),"SCm":("fonts/SC500.woff2",500),
       "Serif":("fonts/Serif700.woff2",700),"Mono":("fonts/Mono600.woff2",600)}
fontface="\n".join(f"@font-face{{font-family:'{f}';font-weight:{w};src:url(data:font/woff2;base64,{b64(p)}) format('woff2')}}"
                   for f,(p,w) in FONTS.items())

# ---- 字幕 ----
GROUPS=json.loads((HERE/(sys.argv[1] if len(sys.argv)>1 else "groups.full.json")).read_text(encoding="utf-8"))
def wrap(t,hls):
    o=html.escape(t)
    for x in (hls or []): o=o.replace(html.escape(x),f"<span class=hl>{html.escape(x)}</span>",1)
    return o
caps="\n".join(f'<div class="{"cg b" if g.get("style")=="b" else "cg"}" id="cg-{i}">'
               f'<div class="cn">{wrap(g["cn"],g.get("hl"))}</div>'
               f'<div class="en">{wrap(g["en"],g.get("enhl"))}</div></div>' for i,g in enumerate(GROUPS))

# ---- widgets ----
WIDGETS=json.loads((HERE/"widgets.json").read_text(encoding="utf-8"))
def wg(i,w):
    k=w["kind"]
    if k=="podcast":
        return (f'<div class="wg" id="wg-{i}"><div class="card podcard">'
                f'<div class="pcover"><img src="{img64(w["cover"])}"><span class="pplay">▶</span></div>'
                f'<div class="wsrc"><span class="dot"></span>{html.escape(w["src"])}</div>'
                f'<div class="ptitle">{html.escape(w["title"])}</div>'
                f'<div class="pguest">{html.escape(w["guest"])}</div></div></div>')
    if k=="duel":
        L,R=w["left"],w["right"]
        return (f'<div class="wg" id="wg-{i}"><div class="card"><div class="duel">'
                f'<div class="dcol"><div class="dlabel">{html.escape(L["label"])}</div><div class="dval">{html.escape(L["val"])}</div></div>'
                f'<div class="dvs">VS</div>'
                f'<div class="dcol big"><div class="dlabel">{html.escape(R["label"])}</div><div class="dval">{html.escape(R["val"])}</div></div>'
                f'</div><div class="dcap">{html.escape(w["cap"])}</div></div></div>')
    if k=="quote":
        return (f'<div class="wg" id="wg-{i}"><div class="card">'
                f'<div class="qmark">&ldquo;</div><div class="qtext">{w["quote"]}</div>'
                f'<div class="qattr">{html.escape(w["attr"])}</div></div></div>')
    if k=="book":
        return (f'<div class="wg" id="wg-{i}"><div class="card"><div class="wrow">'
                f'<img class="bookcover" src="{img64(w["cover"])}">'
                f'<div class="wstatbox"><div class="bookbig">{w["big"]}</div>'
                f'<div class="booksrc">{html.escape(w["src"])}</div>'
                f'<div class="wlabel">{w["label"]}</div></div></div></div></div>')
    if k=="chart":
        # 自绘双线脱钩图：生产率↑(amber) vs 工资→(grey)
        svg=('<svg class="decsvg" viewBox="0 0 520 220" preserveAspectRatio="none">'
             '<line x1="40" y1="180" x2="510" y2="180" stroke="rgba(255,255,255,.18)" stroke-width="2"/>'
             '<line x1="40" y1="20" x2="40" y2="180" stroke="rgba(255,255,255,.18)" stroke-width="2"/>'
             '<polyline points="40,176 150,150 260,110 370,62 500,24" fill="none" stroke="#E9B949" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
             '<polyline points="40,176 150,172 260,168 370,166 500,162" fill="none" stroke="#9AA0A6" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
             '<text x="505" y="20" fill="#E9B949" font-size="22" font-family="Mono" text-anchor="end">生产率</text>'
             '<text x="505" y="150" fill="#9AA0A6" font-size="22" font-family="Mono" text-anchor="end">工资</text></svg>')
        return (f'<div class="wg" id="wg-{i}"><div class="card">'
                f'<div class="wsrc"><span class="dot"></span>{html.escape(w["title"])}</div>'
                f'{svg}<div class="wlabel">{html.escape(w["note"])}</div></div></div>')
    if k=="versus":
        L,R=w["left"],w["right"]
        col=lambda c,cls:(f'<div class="vcol {cls}"><div class="vtag">{html.escape(c["tag"])}</div>'
                          f'<img src="{img64(c["img"])}"><div class="vcap">{c["cap"]}</div></div>')
        return (f'<div class="wg" id="wg-{i}"><div class="card"><div class="versus">'
                f'{col(L,"old")}<div class="dvs">VS</div>{col(R,"new")}</div></div></div>')
    if k=="clip":
        # 真访谈视频片段(PiP)：.wg 壳做透明度动画(无 data 属性)，内层 <video> 带 hyperframes track 属性
        ti=w.get("track",5)
        return (f'<div class="wg" id="wg-{i}"><div class="card clipcard">'
                f'<div class="wtag">{html.escape(w.get("tag","原片"))}</div>'
                f'<div class="wsrc"><span class="dot"></span>{html.escape(w["src_label"])}</div>'
                f'<div class="clipwrap"><video id="clipvid-{i}" class="clipvid" data-start="{w["start"]}" data-duration="{w["srclen"]}" '
                f'data-track-index="{ti}" data-media-start="{w.get("media_start",0)}" src="{w["src"]}" muted playsinline></video></div>'
                f'<div class="cliptext">{wrap(w["en"],w.get("enhl"))}</div></div></div>')
    if k=="titlecard":
        # 大字砸入报幕卡（每段/每个坑开头，无磨砂框，直接大字上画面）
        t=html.escape(w["title"])
        acc=w.get("accent")
        if acc: t=t.replace(html.escape(acc),f"<span class=tchl>{html.escape(acc)}</span>",1)
        t=t.replace("\n","<br>")
        eb=f'<div class="tceyebrow">{html.escape(w["eyebrow"])}</div>' if w.get("eyebrow") else ""
        return (f'<div class="wg" id="wg-{i}"><div class="titlecard">{eb}<div class="tctitle">{t}</div></div></div>')
    if k=="recap":
        # 总结卡：逐条点亮（每行在对应金句时间从灰→金）
        sub=f'<div class="recsub">{html.escape(w["sub"])}</div>' if w.get("sub") else ""
        rows="".join(
          f'<div class="recrow" id="rec-{i}-{j}"><span class="recnum">{html.escape(r["n"])}</span>'
          f'<span class="recname">{html.escape(r["name"])}</span>'
          f'<span class="recdesc">{html.escape(r["desc"])}</span></div>'
          for j,r in enumerate(w["rows"]))
        return (f'<div class="wg" id="wg-{i}"><div class="card recapcard">'
                f'<div class="rectitle">{html.escape(w["title"])}</div>{sub}{rows}</div></div>')
    # news
    photo=(f'<img class="wphoto" src="{img64(w["photo"])}">' if w.get("photo") else "")
    ss=56 if len(w["stat"])>6 else 92
    return (f'<div class="wg" id="wg-{i}"><div class="card">'
            f'<div class="wtag">{html.escape(w.get("tag","实锤"))}</div>'
            f'<div class="wsrc"><span class="dot"></span>{html.escape(w["src"])}</div>'
            f'<div class="whead"><img src="{img64(w["head"])}"></div>'
            f'<div class="wrow">{photo}<div class="wstatbox">'
            f'<div><span class="wstat" style="font-size:{ss}px">{html.escape(w["stat"])}</span>'
            f'<span class="wunit">{html.escape(w.get("unit",""))}</span></div>'
            f'<div class="wlabel">{w["label"]}</div></div></div></div></div>')
wgs="\n".join(wg(i,w) for i,w in enumerate(WIDGETS))
recap_act=[{"wi":i,"ri":j,"t":r["t"]} for i,w in enumerate(WIDGETS) if w.get("kind")=="recap"
           for j,r in enumerate(w["rows"])]

# ---- 章节进度条 ----（本片数据：CWD/chapters.json，缺省回退到内置默认，保持向后兼容）
_chp=HERE/"chapters.json"
if _chp.exists():
    _cj=json.loads(_chp.read_text(encoding="utf-8"))
    CHAPTERS=[tuple(c) for c in _cj["chapters"]]
    VIDEO_DUR=_cj.get("video_dur",1e9)
else:
    CHAPTERS=[(0,34.42,"开场"),(34.42,103.66,"两个数字"),(103.66,178.66,"真账本"),
              (178.66,248.66,"铁证"),(248.66,289.40,"大脱钩"),(289.40,354.16,"护城河")]
    VIDEO_DUR=354.35
chap_dom="\n".join(f'<div class="chseg" style="flex-grow:{t1-t0:.1f}"><div class="chlabel" id="chl-{i}">{lab}</div>'
                   f'<div class="chtrack"><div class="chfill" id="chf-{i}"></div></div></div>'
                   for i,(t0,t1,lab) in enumerate(CHAPTERS))

DUR=min(max(g["end"] for g in GROUPS)+0.6,VIDEO_DUR)

out=f"""<!doctype html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
{fontface}
#root{{position:relative;width:1080px;height:1920px;background:#000;overflow:hidden;font-family:'SC',sans-serif}}
#vid{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
#scrim{{position:absolute;left:0;right:0;bottom:0;height:46%;background:linear-gradient(to bottom,rgba(0,0,0,0) 0%,rgba(0,0,0,.32) 45%,rgba(0,0,0,.82) 100%);pointer-events:none}}
#scrimtop{{position:absolute;left:0;right:0;top:0;height:15%;background:linear-gradient(to top,rgba(0,0,0,0) 0%,rgba(0,0,0,.45) 70%,rgba(0,0,0,.7) 100%);pointer-events:none}}
#caps,#widgets,#chapters{{position:absolute;pointer-events:none}}
#caps,#widgets{{inset:0}}
.cg{{position:absolute;left:0;right:0;bottom:360px;text-align:center;padding:0 72px;opacity:0;will-change:transform,opacity}}
.cn{{font-family:'SC';font-weight:900;font-size:60px;line-height:1.3;color:#F4F1EA;letter-spacing:-.01em;text-shadow:0 2px 18px rgba(0,0,0,.55)}}
.en{{font-family:'Mono';font-weight:600;font-size:31px;line-height:1.38;color:#E7E4DC;letter-spacing:.01em;margin-top:15px;text-shadow:0 2px 12px rgba(0,0,0,.6)}}
.cg.b .cn{{font-size:70px;color:#F8F5EE}}
.hl{{color:#E9B949}}
.wg{{position:absolute;left:56px;right:56px;top:140px;opacity:0;will-change:transform,opacity}}
.card{{position:relative;background:rgba(15,16,19,.76);backdrop-filter:blur(26px) saturate(1.15);-webkit-backdrop-filter:blur(26px) saturate(1.15);border:1px solid rgba(255,255,255,.12);border-radius:28px;padding:30px 32px 32px;box-shadow:0 30px 80px rgba(0,0,0,.55)}}
.wtag{{position:absolute;top:-1px;right:30px;background:#E9B949;color:#0F1013;font-family:'Mono';font-weight:600;font-size:19px;letter-spacing:.1em;padding:7px 14px;border-radius:0 0 10px 10px}}
.wsrc{{display:flex;align-items:center;gap:11px;font-family:'Mono';font-weight:600;font-size:22px;letter-spacing:.08em;color:#E9B949;margin-bottom:18px}}
.dot{{width:9px;height:9px;border-radius:50%;background:#E9B949;box-shadow:0 0 12px #E9B949;flex:none}}
.whead{{border-radius:11px;overflow:hidden;border:1px solid rgba(255,255,255,.10);margin-bottom:22px;background:#fff;line-height:0}}
.whead img{{width:100%;display:block}}
.wrow{{display:flex;align-items:center;gap:24px}}
.wphoto{{width:210px;height:140px;border-radius:13px;object-fit:cover;border:1px solid rgba(255,255,255,.12);flex:none}}
.wstatbox{{flex:1}}
.wstat{{font-family:'SC';font-weight:900;color:#E9B949;letter-spacing:-.02em;line-height:1}}
.wunit{{font-family:'SC';font-weight:900;font-size:38px;color:#F4F1EA;margin-left:8px}}
.wlabel{{font-family:'SCm';font-weight:500;font-size:27px;color:#C9CDD2;margin-top:13px;line-height:1.4}}
/* podcast */
.pcover{{position:relative;border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.12);margin-bottom:20px;line-height:0}}
.pcover img{{width:100%;display:block}}
.pplay{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:84px;height:84px;border-radius:50%;background:rgba(15,16,19,.66);color:#fff;font-size:34px;display:flex;align-items:center;justify-content:center;padding-left:6px;backdrop-filter:blur(4px)}}
.ptitle{{font-family:'SC';font-weight:900;font-size:42px;color:#F4F1EA;line-height:1.25;margin-top:4px}}
.pguest{{font-family:'Mono';font-weight:600;font-size:24px;color:#9AA0A6;letter-spacing:.04em;margin-top:12px}}
/* book */
.bookcover{{width:188px;height:266px;object-fit:cover;border-radius:10px;border:1px solid rgba(255,255,255,.14);flex:none;box-shadow:0 14px 36px rgba(0,0,0,.5)}}
.bookbig{{font-family:'Serif';font-weight:700;font-size:96px;color:#E9B949;line-height:1;letter-spacing:.02em}}
.booksrc{{font-family:'Mono';font-weight:600;font-size:23px;color:#C9CDD2;margin-top:14px;letter-spacing:.03em}}
/* chart */
.decsvg{{width:100%;height:240px;display:block;margin:6px 0 8px}}
/* versus */
.versus{{display:flex;align-items:stretch;gap:16px}}
.vcol{{flex:1;text-align:center}}
.vcol img{{width:100%;height:230px;object-fit:cover;border-radius:13px;border:1px solid rgba(255,255,255,.12)}}
.vcol.new img{{border-color:rgba(233,185,73,.5)}}
.vtag{{font-family:'Mono';font-weight:600;font-size:22px;letter-spacing:.1em;color:#9AA0A6;margin-bottom:10px}}
.vcol.new .vtag{{color:#E9B949}}
.vcap{{font-family:'SC';font-weight:900;font-size:30px;color:#F4F1EA;margin-top:14px;line-height:1.3}}
/* clip：真访谈视频片段 */
.clipwrap{{border-radius:14px;overflow:hidden;border:1px solid rgba(255,255,255,.12);margin-bottom:18px;line-height:0;background:#000}}
.clipvid{{width:100%;display:block}}
.cliptext{{font-family:'Mono';font-weight:600;font-size:27px;line-height:1.4;color:#E7E4DC;letter-spacing:.01em}}
/* titlecard：大字砸入报幕卡 */
.tceyebrow{{font-family:'Mono';font-weight:600;font-size:25px;letter-spacing:.22em;color:#E9B949;margin-bottom:20px}}
.tctitle{{font-family:'SC';font-weight:900;font-size:92px;line-height:1.05;color:#F4F1EA;letter-spacing:-.01em;text-shadow:0 3px 22px rgba(0,0,0,.6)}}
.tchl{{color:#E9B949}}
/* recap：总结卡，逐条点亮 */
.rectitle{{font-family:'SC';font-weight:900;font-size:44px;color:#F4F1EA;letter-spacing:-.01em}}
.recsub{{font-family:'Mono';font-weight:600;font-size:24px;color:#9AA0A6;letter-spacing:.04em;margin-top:6px;margin-bottom:8px}}
.recrow{{display:flex;align-items:baseline;gap:20px;padding:14px 2px;border-top:1px solid rgba(255,255,255,.09);opacity:.34}}
.recnum{{font-family:'Mono';font-weight:600;font-size:30px;color:#9AA0A6;flex:none;width:30px}}
.recname{{font-family:'SC';font-weight:900;font-size:39px;color:#F4F1EA;flex:none}}
.recdesc{{font-family:'SCm';font-weight:500;font-size:28px;color:#C9CDD2;margin-left:auto;text-align:right;line-height:1.3}}
.duel{{display:flex;align-items:stretch;gap:18px}}
.dcol{{flex:1;display:flex;flex-direction:column;align-items:center;padding:6px 2px}}
.dlabel{{font-family:'Mono';font-weight:600;font-size:21px;letter-spacing:.05em;color:#9AA0A6;margin-bottom:14px;text-transform:uppercase}}
.dval{{font-family:'SC';font-weight:900;font-size:58px;color:#8A8F96;letter-spacing:-.02em;display:flex;align-items:center;justify-content:center;min-height:96px}}
.dcol.big .dval{{font-size:92px;color:#E9B949}}
.dvs{{align-self:center;margin-top:30px;font-family:'Mono';font-weight:600;font-size:24px;color:#E9B949}}
.dcap{{font-family:'SC';font-weight:900;font-size:33px;color:#F4F1EA;text-align:center;margin-top:20px}}
.qmark{{font-family:'Serif';font-weight:700;font-size:74px;color:#E9B949;line-height:.5;height:34px}}
.qtext{{font-family:'Serif';font-weight:700;font-size:48px;line-height:1.42;color:#F4F1EA}}
.qattr{{font-family:'Mono';font-weight:600;font-size:22px;letter-spacing:.05em;color:#E9B949;margin-top:22px}}
/* 章节进度条（置顶） */
#chapters{{left:24px;right:24px;top:40px;display:flex;gap:9px;align-items:flex-start}}
.chseg{{flex-basis:0}}
.chlabel{{font-family:'Mono';font-weight:600;font-size:23px;letter-spacing:.02em;text-align:center;margin-bottom:9px;color:#6B7075;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 6px rgba(0,0,0,.7)}}
.chtrack{{height:6px;border-radius:3px;background:rgba(255,255,255,.20);overflow:hidden}}
.chfill{{height:100%;width:100%;background:#E9B949;transform:scaleX(0);transform-origin:left center;border-radius:3px}}
</style></head><body>
<div id="root" data-composition-id="root" data-width="1080" data-height="1920" data-start="0" data-duration="{DUR:.2f}">
  <video id="vid" data-start="0" data-duration="{DUR:.2f}" data-track-index="0" data-media-start="0" src="video.mp4" muted playsinline></video>
  <audio id="aud" data-start="0" data-duration="{DUR:.2f}" data-track-index="2" src="video.mp4" data-volume="1"></audio>
  <div id="scrim"></div>
  <div id="scrimtop"></div>
  <div id="widgets">
{wgs}
  </div>
  <div id="caps">
{caps}
  </div>
  <div id="chapters">
{chap_dom}
  </div>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
  window.__timelines=window.__timelines||{{}};
  const GROUPS={json.dumps([{k:g[k] for k in ('start','end','style')} for g in GROUPS])};
  const WIDGETS={json.dumps([{k:w[k] for k in ('start','end','kind')} for w in WIDGETS])};
  const CH={json.dumps([[t0,t1] for t0,t1,_ in CHAPTERS])};
  const tl=gsap.timeline({{paused:true}});
  GROUPS.forEach(function(g,i){{
    var el=document.getElementById('cg-'+i); if(!el)return;
    if(g.style==='b') tl.fromTo(el,{{opacity:0,y:30,scale:.92}},{{opacity:1,y:0,scale:1,duration:.40,ease:'back.out(1.6)'}},g.start);
    else tl.fromTo(el,{{opacity:0,y:24}},{{opacity:1,y:0,duration:.32,ease:'power3.out'}},g.start);
    tl.to(el,{{opacity:0,y:-14,duration:.18,ease:'power2.in'}},g.end-.18);
    tl.set(el,{{opacity:0,visibility:'hidden'}},g.end);
  }});
  WIDGETS.forEach(function(w,i){{
    var el=document.getElementById('wg-'+i); if(!el)return;
    if(w.kind==='titlecard') tl.fromTo(el,{{opacity:0,scale:1.18,y:-12}},{{opacity:1,scale:1,y:0,duration:.5,ease:'back.out(1.8)'}},w.start);
    else tl.fromTo(el,{{opacity:0,y:-30,scale:.97}},{{opacity:1,y:0,scale:1,duration:.55,ease:'power3.out'}},w.start);
    tl.to(el,{{opacity:0,y:-18,duration:.35,ease:'power2.in'}},w.end-.35);
    tl.set(el,{{opacity:0,visibility:'hidden'}},w.end);
  }});
  const RECAP={json.dumps(recap_act)};
  RECAP.forEach(function(r){{
    var el=document.getElementById('rec-'+r.wi+'-'+r.ri); if(!el)return;
    tl.to(el,{{opacity:1,duration:.34,ease:'power2.out'}},r.t);
    tl.to(el.querySelector('.recnum'),{{color:'#E9B949',duration:.34}},r.t);
    tl.to(el.querySelector('.recname'),{{color:'#F8F5EE',duration:.34}},r.t);
  }});
  CH.forEach(function(c,i){{
    var f=document.getElementById('chf-'+i), l=document.getElementById('chl-'+i);
    tl.fromTo(f,{{scaleX:0}},{{scaleX:1,duration:Math.max(c[1]-c[0],.1),ease:'none'}},c[0]);
    tl.set(l,{{color:'#E9B949'}},c[0]);
    tl.set(l,{{color:'#C9CDD2'}},c[1]-.01);
  }});
  tl.seek(0);
  window.__timelines['root']=tl;
  </script>
</div></body></html>"""
# ---- 主题配色（本片 theme.json 覆盖默认琥珀；无 theme.json 则不变，旧片不受影响）----
_thm=HERE/"theme.json"
if _thm.exists():
    T=json.loads(_thm.read_text(encoding="utf-8"))
    repl={
      "#F4F1EA":T.get("bone","#F4F1EA"), "#F8F5EE":T.get("bone_bright","#F8F5EE"),
      "#E7E4DC":T.get("en","#E7E4DC"), "#9AA0A6":T.get("graphite","#9AA0A6"),
      "#C9CDD2":T.get("graphite2","#C9CDD2"), "#E9B949":T.get("accent","#E9B949"),
      "#0F1013":T.get("ink","#0F1013"), "#6B7075":T.get("dim","#6B7075"),
      "#8A8F96":T.get("weak","#8A8F96"),
      "15,16,19":T.get("ink_rgb","15,16,19"), "233,185,73":T.get("accent_rgb","233,185,73"),
    }
    for a,b in repl.items(): out=out.replace(a,b)
    print(f"theme applied: accent {T.get('accent')}")

(HERE/"index.html").write_text(out,encoding="utf-8")
print(f"wrote index.html — {len(GROUPS)} caps + {len(WIDGETS)} widgets + {len(CHAPTERS)} chapters")
