"""Map Claude-written extraction records onto the schema enums and load as pass1.
Anything that cannot be mapped is set to 'unknown' and noted. Run: python tools/normalize_extractions.py"""
import glob, json, sys
sys.path.insert(0, ".")
from src import schema as S
MAP = {
 "auth_methods": {"jwt":"other","none":"none_found"},
 "api_type": {"mcp":None,"cli_only":"none_public"},
 "main_blocker": {"app_review":"admin_approval","no_api":"no_public_api"},
}
def norm(r):
    notes=[]
    for k,m in MAP.items():
        v=r[k]
        if isinstance(v,list):
            out=[]
            for x in v:
                y=m.get(x,x)
                if y is None: notes.append(f"dropped {k}={x}"); continue
                if y!=x: notes.append(f"{k}:{x}->{y}")
                out.append(y)
            r[k]=out or ["unknown"]
        else:
            y=m.get(v,v)
            if y!=v: notes.append(f"{k}:{v}->{y}")
            r[k]=y
    r["_norm"]=notes
    return r
def load():
    recs=[]
    for f in sorted(glob.glob("data/extraction/b*.json")):
        recs+= [norm(r) for r in json.load(open(f, encoding="utf-8"))]
    return recs
if __name__=="__main__":
    recs=load(); print(len(recs),"records")
    for r in recs:
        if r["_norm"]: print(r["app"],r["_norm"])
