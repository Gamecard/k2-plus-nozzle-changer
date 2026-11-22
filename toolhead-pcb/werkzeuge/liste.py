import sys, pcbnew
b=pcbnew.LoadBoard(sys.argv[1]); x0,y0,x1,y1=map(float,sys.argv[2:6]); nets=sys.argv[6].split(",") if len(sys.argv)>6 and sys.argv[6] else None
O=(50,40)
def M(v): return (round(pcbnew.ToMM(v.x)-O[0],3),round(pcbnew.ToMM(v.y)-O[1],3))
def inb(p): return x0<=p[0]<=x1 and y0<=p[1]<=y1
for fp in b.GetFootprints():
    for p in fp.Pads():
        c=M(p.GetPosition())
        if inb(c) and (nets is None or p.GetNetname() in nets):
            bb=p.GetBoundingBox(); a=M(bb.GetOrigin()); e=M(bb.GetEnd())
            print(f"PAD {fp.GetReference()}-{p.GetNumber()} {p.GetNetname()} {'B' if fp.IsFlipped() else 'F'}{' THT' if p.GetDrillSize().x>0 else ''} bbox {a} {e}")
for t in b.GetTracks():
    if nets is not None and t.GetNetname() not in nets: continue
    if t.GetClass()=="PCB_VIA":
        c=M(t.GetPosition())
        if inb(c): print(f"VIA {t.GetNetname()} {c} d{pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)):.2f} {'fest' if t.IsLocked() else 'router'}")
    else:
        a,e=M(t.GetStart()),M(t.GetEnd())
        if inb(a) or inb(e): print(f"BAHN {t.GetNetname()} {b.GetLayerName(t.GetLayer())} {a}->{e} w{pcbnew.ToMM(t.GetWidth()):.3f} {'fest' if t.IsLocked() else 'router'}")
