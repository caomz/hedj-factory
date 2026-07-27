#!/usr/bin/env python3
"""Faithful triggering harness for hedj-factory.

Writes a candidate description into the REAL installed skill, then for each query
runs `claude -p` and records which skill claude picks FIRST (killing the process
the moment it decides, so it's fast and never executes the pipeline).

Goal: should_trigger=True  -> first skill should be hedj-factory
      should_trigger=False -> first skill should be anything-but hedj-factory
"""
import json, os, re, select, subprocess, sys, time, concurrent.futures as cf

SKILL_MD = os.path.expanduser("~/.claude/skills/hedj-factory/SKILL.md")
MODEL = "claude-opus-4-8"
RUNS = int(os.environ.get("HEDJ_RUNS", "2"))
TIMEOUT = 70

def set_description(desc):
    txt = open(SKILL_MD).read()
    # replace the frontmatter description block (description: | ... up to next top-level key)
    new = re.sub(r"(?ms)^description:.*?(?=^---)", "description: |\n" + "".join("  "+l+"\n" for l in desc.strip().split("\n")), txt, count=1)
    open(SKILL_MD, "w").write(new)

def first_skill(query):
    """Return name of first skill claude invokes, or '<tool:Bash>' / '<none>'."""
    cmd = ["claude","-p",query,"--output-format","stream-json","--verbose",
           "--include-partial-messages","--model",MODEL]
    env = {k:v for k,v in os.environ.items() if k!="CLAUDECODE"}
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, cwd="/tmp/hedj-opt")
    buf=""; pending=None; acc=""; start=time.time()
    def finish(val):
        try: p.kill()
        except: pass
        return val
    try:
        while time.time()-start < TIMEOUT:
            r,_,_ = select.select([p.stdout],[],[],1.0)
            if r:
                chunk=os.read(p.stdout.fileno(),65536)
                if not chunk:
                    return finish("<none>")  # stream closed, no skill seen
                buf += chunk.decode("utf-8","replace")
            elif p.poll() is not None:
                return finish("<none>")
            while "\n" in buf:
                line,buf=buf.split("\n",1); line=line.strip()
                if not line: continue
                try: e=json.loads(line)
                except: continue
                # ONLY use stream_events; ignore text/preamble. First *tool* decides.
                if e.get("type")=="stream_event":
                    se=e.get("event",{}); t=se.get("type","")
                    if t=="content_block_start":
                        cb=se.get("content_block",{})
                        if cb.get("type")=="tool_use":
                            if cb.get("name")=="Skill": pending="Skill"; acc=""
                            else: return finish(f"<tool:{cb.get('name')}>")
                    elif t=="content_block_delta" and pending=="Skill":
                        d=se.get("delta",{})
                        if d.get("type")=="input_json_delta":
                            acc+=d.get("partial_json","")
                            m=re.search(r'"skill"\s*:\s*"([^"]+)"', acc)
                            if m: return finish(m.group(1))
                    elif t=="content_block_stop" and pending=="Skill":
                        m=re.search(r'"skill"\s*:\s*"([^"]+)"', acc)
                        return finish(m.group(1) if m else "<skill:?>")
                elif e.get("type")=="result":
                    return finish("<none>")  # turn ended with no tool
        return finish("<timeout>")
    except Exception as ex:
        return finish(f"<err:{type(ex).__name__}>")

def run(queries):
    out=[]
    def one(item):
        q=item["query"]; picks=[first_skill(q) for _ in range(RUNS)]
        rate=sum(1 for x in picks if x=="hedj-factory")/len(picks)
        return {"query":q,"should":item["should_trigger"],"rate":rate,"picks":picks}
    with cf.ThreadPoolExecutor(max_workers=int(os.environ.get("BKF_WORKERS","3"))) as ex:
        out=list(ex.map(one, queries))
    return out

if __name__=="__main__":
    desc=open(sys.argv[2]).read() if len(sys.argv)>2 else None
    if desc: set_description(desc)
    evs=json.load(open(sys.argv[1]))
    res=run(evs)
    tp=tn=fp=fn=0
    for r in res:
        trig=r["rate"]>=0.5
        if r["should"] and trig: tp+=1
        elif r["should"] and not trig: fn+=1
        elif not r["should"] and trig: fp+=1
        else: tn+=1
    print(json.dumps({"results":res,"tp":tp,"tn":tn,"fp":fp,"fn":fn,
        "recall":tp/(tp+fn) if tp+fn else 0,"precision":tp/(tp+fp) if tp+fp else 0,
        "acc":(tp+tn)/len(res)}, ensure_ascii=False, indent=2))
