#!/usr/bin/env python3
# take.py — 取片三模式：①抖音作者枚举(全自动) ②视频号作者(半自动,吃 wx 抓的 feed) ③单链下载
# 配合 video-distill：枚举→按热度列出→你勾选→下载→交给 transcribe.sh + 拆解。
#
# 用法：
#   python take.py douyin <作者主页URL或sec_uid> [--top 20] [--all]   # 枚举抖音作者全部作品(只取metadata)
#   python take.py sphfeed <wx抓的feed.json>                          # 视频号作者：解析wx_channels_download抓到的feed列表
#   python take.py dl <works.json> <序号,逗号分隔> <输出目录>           # 下载选中的作品到 案例库/<...>
#   python take.py one <单条链接> <输出目录>                           # 单链：抖音视频 / 视频号分享链 自动判别下载
#
# 依赖：抖音枚举要 `pip install f2`；cookie 放 ~/.baokuan-factory/secrets.env(DOUYIN_COOKIE=...)，
#       没有就试浏览器自动取(需登录抖音)。视频号用在线解析器 sph.litao.workers.dev。
# 去重：已蒸馏的 id 记在 ~/.baokuan-factory/state/distilled.json，枚举时自动跳过(--all 显示全部)。
import sys, os, json, re, subprocess, pathlib, asyncio

STATE = pathlib.Path.home() / ".baokuan-factory" / "state"
STATE.mkdir(parents=True, exist_ok=True)
REGISTRY = STATE / "distilled.json"
SECRETS = pathlib.Path.home() / ".baokuan-factory" / "secrets.env"

def load_secrets():
    env = {}
    if SECRETS.exists():
        for line in SECRETS.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def reg_load():
    return set(json.loads(REGISTRY.read_text())) if REGISTRY.exists() else set()
def reg_add(ids):
    s = reg_load() | set(ids); REGISTRY.write_text(json.dumps(sorted(s), ensure_ascii=False, indent=1))

# ---------- 抖音 ----------
def douyin_cookie():
    env = load_secrets()
    if env.get("DOUYIN_COOKIE"): return env["DOUYIN_COOKIE"]
    # 兜底：从浏览器取(需登录抖音)
    try:
        import browser_cookie3 as bc
        for loader in (bc.safari, bc.chrome, bc.edge):
            try:
                cj = loader(domain_name="douyin.com")
                ck = "; ".join(f"{c.name}={c.value}" for c in cj)
                if "sessionid" in ck or len(ck) > 50: return ck
            except Exception: continue
    except Exception: pass
    return ""

def douyin_handler(cookie):
    from f2.apps.douyin.handler import DouyinHandler
    from f2.utils.conf_manager import ConfigManager
    import f2, os as _os
    conf = ConfigManager(_os.path.join(_os.path.dirname(f2.__file__), "conf/app.yaml")).get_config("douyin")
    conf = dict(conf or {})
    conf["cookie"] = cookie
    conf.setdefault("headers", {"User-Agent": "Mozilla/5.0", "Referer": "https://www.douyin.com/"})
    conf.setdefault("proxies", {"http://": None, "https://": None})
    conf["timeout"] = int(load_secrets().get("DOUYIN_INTERVAL", 3))   # f2 拿 timeout 当翻页间隔，默认10太慢
    return DouyinHandler(conf)

async def douyin_enum(url_or_uid, top, show_all):
    from f2.apps.douyin.utils import SecUserIdFetcher
    cookie = douyin_cookie()
    if not cookie:
        print("❌ 没拿到抖音 cookie。两选一：\n"
              "   a) 把 DOUYIN_COOKIE=... 写进 ~/.baokuan-factory/secrets.env\n"
              "   b) 在 Safari/Chrome 登录抖音,装 `pip install browser_cookie3` 自动取", file=sys.stderr)
        sys.exit(2)
    sec = url_or_uid
    if url_or_uid.startswith("http"):
        sec = await SecUserIdFetcher.get_sec_user_id(url_or_uid)
    h = douyin_handler(cookie)
    done = reg_load()
    works = []
    # 列表的 _to_dict() 不带点赞数；_to_raw().aweme_list 里每条有完整 statistics，直接取。
    async for page in h.fetch_user_post_videos(sec, page_counts=20, max_counts=None):
        raw = page._to_raw() if hasattr(page, "_to_raw") else {}
        for a in raw.get("aweme_list") or []:
            aid = str(a.get("aweme_id") or "")
            if not aid:
                continue
            st = a.get("statistics") or {}
            works.append({"aweme_id": aid, "desc": (a.get("desc") or "").replace("\n", " ")[:60],
                          "digg": st.get("digg_count", 0), "collect": st.get("collect_count", 0),
                          "comment": st.get("comment_count", 0), "share": st.get("share_count", 0),
                          "create_time": a.get("create_time"),
                          "share_url": f"https://www.douyin.com/video/{aid}"})
    if not show_all:
        works = [w for w in works if w["aweme_id"] not in done]
    works.sort(key=lambda w: int(w["digg"] or 0), reverse=True)
    return works

# ---------- 视频号 ----------
def sph_feed_parse(feed_json):
    """解析 wx_channels_download 抓到的作者 feed 列表(/api/channels/feed/profile 之类)。"""
    raw = json.loads(pathlib.Path(feed_json).read_text())
    items = raw.get("data") or raw.get("list") or raw.get("feeds") or (raw if isinstance(raw, list) else [])
    done = reg_load(); works = []
    for it in items:
        oid = str(it.get("objectId") or it.get("id") or it.get("exportId") or "")
        if not oid or oid in done: continue
        works.append({"object_id": oid, "desc": (it.get("description") or it.get("desc") or "").replace("\n", " ")[:60],
                      "like": it.get("likeCount") or it.get("like_count") or 0,
                      "fav": it.get("favCount") or 0, "forward": it.get("forwardCount") or 0,
                      "video_url": it.get("videoUrl") or it.get("url") or ""})
    works.sort(key=lambda w: int(w.get("like") or 0), reverse=True)
    return works

def sph_resolve(share_url):
    """单条视频号分享链 → 真链(明文mp4)。走 sph.litao.workers.dev(用 curl 避开 Python 证书问题)。"""
    out = subprocess.run(["curl", "-fsS", "-X", "POST",
        "https://sph.litao.workers.dev/api/fetch_video_profile",
        "-H", "Content-Type: application/json", "-d", json.dumps({"url": share_url})],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)["data"]
    fi = d["feedInfo"]
    return {"object_id": str(fi.get("exportId") or fi.get("id") or ""), "video_url": fi["videoUrl"],
            "desc": fi.get("description", ""), "nickname": d.get("authorInfo", {}).get("nickname", "")}

# ---------- 下载 ----------
UA_WX = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 WeChat"
def curl_dl(url, out, wx=False):
    cmd = ["curl", "-fsSL", url, "-o", out]
    if wx: cmd[2:2] = ["-H", f"User-Agent: {UA_WX}", "-H", "Referer: https://channels.weixin.qq.com/"]
    subprocess.run(cmd, check=True)

def md_table(works):
    if not works: return "（没有新作品，全部已蒸馏过。--all 看全部）"
    out = ["| # | 赞 | 收藏 | 评 | 文案 | id |", "|--|--|--|--|--|--|"]
    for i, w in enumerate(works):
        likes = w.get("digg", w.get("like", "-")); fav = w.get("collect", w.get("fav", "-"))
        cm = w.get("comment", "-"); wid = w.get("aweme_id") or w.get("object_id")
        out.append(f"| {i} | {likes} | {fav} | {cm} | {w['desc']} | {wid} |")
    return "\n".join(out)

def main():
    if len(sys.argv) < 2: print(__doc__ or "见文件头注释"); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "douyin":
        url = sys.argv[2]; top = None; show_all = "--all" in sys.argv
        if "--top" in sys.argv: top = int(sys.argv[sys.argv.index("--top") + 1])
        works = asyncio.run(douyin_enum(url, top, show_all))
        if top: works = works[:top]
        outp = STATE / "douyin_works.json"; outp.write_text(json.dumps(works, ensure_ascii=False, indent=1))
        print(md_table(works)); print(f"\n→ {len(works)} 条已存 {outp}。下载选中：python take.py dl {outp} 0,1,2 案例库/<作者>")
    elif cmd == "sphfeed":
        works = sph_feed_parse(sys.argv[2])
        outp = STATE / "sph_works.json"; outp.write_text(json.dumps(works, ensure_ascii=False, indent=1))
        print(md_table(works)); print(f"\n→ {len(works)} 条已存 {outp}。下载：python take.py dl {outp} 0,1 案例库/<作者>")
    elif cmd == "dl":
        works = json.loads(pathlib.Path(sys.argv[2]).read_text())
        idxs = [int(x) for x in sys.argv[3].split(",")]; outdir = pathlib.Path(sys.argv[4]); outdir.mkdir(parents=True, exist_ok=True)
        ids = []
        for i in idxs:
            w = works[i]; wid = w.get("aweme_id") or w.get("object_id"); dest = outdir / f"{wid}.mp4"
            if "video_url" in w and w["video_url"]:           # 视频号
                curl_dl(w["video_url"], str(dest), wx=True)
            else:                                              # 抖音：用 yt-dlp 下分享链(拿无水印)
                subprocess.run(["yt-dlp", "-o", str(dest), w["share_url"]], check=True)
            (outdir / f"{wid}.source.txt").write_text(f"{w.get('share_url') or w.get('video_url')}\n{w['desc']}\n")
            print(f"✓ {dest}"); ids.append(wid)
        reg_add(ids); print(f"已记入去重表 {REGISTRY}（下次枚举自动跳过）")
    elif cmd == "one":
        link, outdir = sys.argv[2], pathlib.Path(sys.argv[3]); outdir.mkdir(parents=True, exist_ok=True)
        if "weixin.qq.com/sph" in link or "channels.weixin" in link:
            r = sph_resolve(link); dest = outdir / f"{r['object_id'] or 'sph'}.mp4"; curl_dl(r["video_url"], str(dest), wx=True)
        else:
            dest = outdir / "video.mp4"; subprocess.run(["yt-dlp", "-o", str(dest), link], check=True)
        print(f"✓ {dest}")
    else:
        print(f"未知命令 {cmd}。见文件头注释。"); sys.exit(1)

if __name__ == "__main__":
    main()
