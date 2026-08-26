#!/usr/bin/env python3
"""Static (keyword/heuristic) trigger evaluation when `claude` CLI is unavailable.

Scores which skill *should* fire based on SKILL.md frontmatter descriptions.
Not a substitute for hedj_eval.py faithful triggering — run that locally with claude.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def parse_frontmatter(skill_md: Path) -> tuple[str, str]:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return "", ""
    fm = m.group(1)
    name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc_m = re.search(r"^description:\s*\|\s*\n((?:  .+\n?)*)", fm, re.M)
    name = name_m.group(1).strip() if name_m else skill_md.parent.name
    desc = desc_m.group(1).replace("  ", "") if desc_m else ""
    return name, desc


def load_skill_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for skill_dir in sorted(SKILLS.iterdir()):
        md = skill_dir / "SKILL.md"
        if not md.exists():
            continue
        name, desc = parse_frontmatter(md)
        profiles[name] = {
            "path": str(md.relative_to(ROOT)),
            "desc": desc,
            "trigger_hints": re.findall(r"[「]([^」]+)[」]", desc),
            "boundary_lines": [
                ln.strip()
                for ln in desc.splitlines()
                if "边界" in ln or "不是本 skill" in ln or "别抢" in ln
            ],
        }
    return profiles


BOOK_STRONG = [
    "讲书", "说书", "拆书", "读书博主", "书籍解读", "听书解读", "书摘视频",
    "这本书", "做成讲书", "讲这本书", "一本书做成",
]
BOOK_WEAK = ["书", "章节", "摘录", "epub", "pdf", "《", "》"]
VIDEO_STRONG = [
    "抖音", "视频号", "小红书.com", "weixin.qq.com/sph", "yt-dlp", "whisper",
    "对标视频", "翻拍这条", "mp4", "取片", "转写",
]
FULL_PIPELINE = [
    "完整链路", "一条龙", "从.*到.*成片", "系统化", "onboarding", "装一下",
    "全流程", "完整走一遍",
]


def score_skill(name: str, desc: str, query: str) -> float:
    q = query.lower()
    score = 0.0

    if name == "book-narration-video":
        score += sum(3 for k in BOOK_STRONG if k in query)
        score += sum(1 for k in BOOK_WEAK if k in query)
        score -= sum(4 for k in VIDEO_STRONG if k in query)
        if "不要成片" in query or ("只要" in query and ("笔记" in query or "感想" in query)):
            score -= 8
        if "不要视频" in query or "不要口播卡片" in query:
            score -= 4
        if "完整链路" in query or "一条龙" in query:
            score -= 2  # defer to hedj-factory
        if "拆解" in query and "爆款" in query and "书" not in query:
            score -= 6

    elif name == "hedj-factory":
        score += sum(2 for k in FULL_PIPELINE if re.search(k, query))
        if "完整" in query and ("成片" in query or "文案" in query):
            score += 2
        if "onboarding" in q or "装一下" in query:
            score += 3
        if "书" in query and ("完整" in query or "一条龙" in query or "全流程" in query):
            score += 3
        score -= 1 if "只要" in query and "笔记" in query else 0

    elif name == "video-distill":
        score += sum(3 for k in VIDEO_STRONG if k in query)
        score += 1 if "拆解" in query and "视频" in query else 0
        score -= 2 if "书" in query and "视频" not in query else 0

    # Generic: trigger hints from description
    hints = re.findall(r"[「]([^」]+)[」]", desc)
    score += sum(2 for h in hints if h in query)

    return score


def pick_skill(query: str, profiles: dict[str, dict], candidates: list[str] | None = None) -> tuple[str, dict[str, float]]:
    cand = candidates or list(profiles.keys())
    scores = {n: score_skill(n, profiles[n]["desc"], query) for n in cand if n in profiles}
    if not scores:
        return "<none>", scores
    top = max(scores.values())
    tied = [n for n, s in scores.items() if s == top]
    if len(tied) == 1:
        return tied[0], scores
    if "hedj-factory" in tied and any(k in query for k in ("完整链路", "一条龙", "onboarding")):
        return "hedj-factory", scores
    if "video-distill" in tied and any(k in query for k in ("视频", "抖音", "视频号", "爆款")):
        return "video-distill", scores
    return tied[0], scores


def run_eval(evals_path: Path, focus_skill: str, candidates: list[str] | None = None) -> dict:
    profiles = load_skill_profiles()
    evs = json.loads(evals_path.read_text(encoding="utf-8"))
    results = []
    tp = tn = fp = fn = 0
    for item in evs:
        q = item["query"]
        should = item["should_trigger"]
        expected = item.get("expected_skill", focus_skill)
        picked, scores = pick_skill(q, profiles, candidates)
        if should:
            ok = picked == expected
            if ok:
                tp += 1
            else:
                fn += 1
        else:
            ok = picked != focus_skill
            if ok:
                tn += 1
            else:
                fp += 1
        results.append({
            "query": q,
            "should_trigger": should,
            "expected": expected,
            "picked": picked,
            "scores": {k: round(v, 1) for k, v in sorted(scores.items(), key=lambda x: -x[1])[:5]},
            "ok": ok,
        })
    n = len(evs)
    return {
        "focus_skill": focus_skill,
        "mode": "static_heuristic",
        "note": "Requires local `claude -p` + hedj_eval.py for faithful triggering validation",
        "results": results,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": round((tp + tn) / n, 3) if n else 0,
        "recall": round(tp / (tp + fn), 3) if (tp + fn) else 0,
        "precision": round(tp / (tp + fp), 3) if (tp + fp) else 0,
    }


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".optimize/book-narration-trigger-evals.json"
    focus = sys.argv[2] if len(sys.argv) > 2 else "book-narration-video"
    cands = ["book-narration-video", "hedj-factory", "video-distill", "talking-head-edit", "hyperframes"]
    out = run_eval(path, focus, cands)
    print(json.dumps(out, ensure_ascii=False, indent=2))
