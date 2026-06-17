#!/usr/bin/env python3
# 静音裁剪：把 >0.5s 的静音段收紧到 ~0.18s 呼吸（每侧留 0.09s 防切到字头字尾），
# 用 ffmpeg select/aselect 一次重编码出紧凑视频。
# 关键纪律：**先 trim 再转写 => 字幕/卡片时间天然对齐紧凑时间轴**。
#   即:先对原片跑本脚本出 <name>_tight.mp4,再把 build/video.mp4 软链到 tight、
#   重抽 audio.wav、转写,后面所有时间(字幕/widgets/chapters)都长在紧凑时间轴上。
#   (若已在原时间轴建好了,可改用 silence_keep.json 把各时间戳 remap 过去,数学等价。)
# 用法：python3 cut_silence.py <原片.mp4> <输出_tight.mp4>
import subprocess, re, sys, json, pathlib

SRC = sys.argv[1] if len(sys.argv) > 1 else "../video.mp4"
OUT = sys.argv[2] if len(sys.argv) > 2 else "tight.mp4"
NOISE = "-30dB"     # 静音判定门限（室噪地板，按录音环境调）
MIN_SIL = 0.5       # 只处理超过 0.5s 的静音
PAD = 0.09          # 每侧保留 0.09s => 收紧后残留约 0.18s 呼吸
FR = 30             # 帧率
# 教训：句尾词的尾音会掉到门限以下被当成静音切掉(如"怎么这么堵"的"堵")。
# 把会误切的原始时间窗填进 PROTECT(t0,t1)：落在窗内的静音整段不裁,保住句尾词 + 包袱后停顿。
PROTECT = []  # 默认空；渲出来发现某句尾被吃了,加一个窗再跑

dur = float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
      "-of","default=nw=1:nk=1", SRC], capture_output=True, text=True).stdout.strip())

log = subprocess.run(["ffmpeg","-hide_banner","-i",SRC,"-af",
      f"silencedetect=noise={NOISE}:d={MIN_SIL}","-f","null","-"],
      capture_output=True, text=True).stderr
sils = []; cur = None
for line in log.splitlines():
    m = re.search(r"silence_start:\s*([\d.]+)", line)
    if m: cur = float(m.group(1))
    m = re.search(r"silence_end:\s*([\d.]+)", line)
    if m and cur is not None:
        sils.append((cur, float(m.group(1)))); cur = None

def protected(ss, se):
    return any(not (se < p0 or ss > p1) for p0, p1 in PROTECT)
remove = []
for ss, se in sils:
    if protected(ss, se): continue
    a, b = ss + PAD, se - PAD
    if b - a > 0.02: remove.append((a, b))

keep = []; t = 0.0
for a, b in remove:
    if a > t: keep.append((t, a))
    t = max(t, b)
if t < dur: keep.append((t, dur))
keep = [(round(a,3), round(b,3)) for a,b in keep if b-a > 0.05]

removed = dur - sum(b-a for a,b in keep)
print(f"原时长 {dur:.1f}s -> 紧凑 {dur-removed:.1f}s（删掉 {removed:.1f}s，{len(sils)} 段静音，{len(keep)} 个保留段）")

sel = "+".join(f"between(t,{a},{b})" for a,b in keep)
vf = f"select='{sel}',setpts=N/{FR}/TB"
af = f"aselect='{sel}',asetpts=N/SR/TB"

pathlib.Path("silence_keep.json").write_text(json.dumps(
    {"src_dur":dur,"out_dur":round(dur-removed,3),"keep":keep,"noise":NOISE,
     "min_sil":MIN_SIL,"pad":PAD}, ensure_ascii=False, indent=1), encoding="utf-8")

cmd = ["ffmpeg","-y","-i",SRC,"-vf",vf,"-af",af,
       "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p",
       "-c:a","aac","-b:a","192k","-movflags","+faststart", OUT]
print("ffmpeg 重编码中…")
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(r.stderr[-2000:]); sys.exit(1)
print(f"写出 {OUT}")
