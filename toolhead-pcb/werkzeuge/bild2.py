import sys, pcbnew
from PIL import Image, ImageDraw
b = pcbnew.LoadBoard(sys.argv[1]); x0,y0,x1,y1 = map(float, sys.argv[2:6]); out=sys.argv[6]; hl=sys.argv[7].split(",") if len(sys.argv)>7 else []
S=float(sys.argv[8]) if len(sys.argv)>8 else 45; O=(50,40)
HC=[(255,0,255),(0,200,255),(255,140,0),(0,220,0)]
def hc(n): return HC[hl.index(n)%4] if n in hl else None
W,H=int((x1-x0)*S),int((y1-y0)*S)
def P(v): return ((pcbnew.ToMM(v.x)-O[0]-x0)*S,(pcbnew.ToMM(v.y)-O[1]-y0)*S)
def inb(v):
    x,y=pcbnew.ToMM(v.x)-O[0],pcbnew.ToMM(v.y)-O[1]; return x0-2<x<x1+2 and y0-2<y<y1+2
bilder=[]
for ly,name in ((pcbnew.F_Cu,"F (L1)"),(pcbnew.In2_Cu,"I2 (L3)"),(pcbnew.In3_Cu,"I3 (L4)"),(pcbnew.B_Cu,"B (L6)")):
    im=Image.new("RGB",(W,H),(255,255,255)); d=ImageDraw.Draw(im)
    for z in b.Zones():
        if z.GetIsRuleArea() and z.IsOnLayer(ly) and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
            ol=z.Outline().Outline(0); pts=[P(ol.CPoint(i)) for i in range(ol.PointCount())]
            if len(pts)>2: d.polygon(pts,fill=(255,235,200))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if not p.IsOnLayer(ly) or not inb(p.GetPosition()): continue
            bb=p.GetBoundingBox(); a=P(bb.GetOrigin()); e=P(bb.GetEnd())
            d.rectangle([a,e],fill=hc(p.GetNetname()) or (170,170,170),outline=(90,90,90))
            if S>=40: d.text((a[0]+1,a[1]+1),f"{fp.GetReference()}-{p.GetNumber()}",fill=(0,0,0))
    for t in b.GetTracks():
        if t.GetClass()=="PCB_VIA": continue
        if t.GetLayer()==ly and (inb(t.GetStart()) or inb(t.GetEnd())):
            c=hc(t.GetNetname()) or ((60,60,60) if t.IsLocked() else (120,150,255))
            d.line([P(t.GetStart()),P(t.GetEnd())],fill=c,width=max(1,int(pcbnew.ToMM(t.GetWidth())*S)))
    for t in b.GetTracks():
        if t.GetClass()=="PCB_VIA" and inb(t.GetPosition()):
            c=P(t.GetPosition()); r=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu))/2*S
            d.ellipse([c[0]-r,c[1]-r,c[0]+r,c[1]+r],fill=hc(t.GetNetname()) or ((0,0,0) if t.IsLocked() else (200,0,0)))
            r2=pcbnew.ToMM(t.GetDrillValue())/2*S; d.ellipse([c[0]-r2,c[1]-r2,c[0]+r2,c[1]+r2],fill=(255,255,255))
    k=int(x0)
    while k<=x1:
        d.line([((k-x0)*S,0),((k-x0)*S,H)],fill=(225,225,225)); d.text(((k-x0)*S+1,0),str(k),fill=(0,120,0)); k+=1
    k=int(y0)
    while k<=y1:
        d.line([(0,(k-y0)*S),(W,(k-y0)*S)],fill=(225,225,225)); d.text((0,(k-y0)*S+1),str(k),fill=(0,120,0)); k+=1
    d.text((W-70,12),name,fill=(200,0,0)); bilder.append(im)
import os
einzel=os.environ.get("EINZEL")
if einzel:
    for i,n in enumerate("F I2 I3 B".split()):
        if n in einzel.split(","): bilder[i].save(out.replace(".png",f"_{n}.png"))
else:
    g=Image.new("RGB",(W*2+10,H*2+10),(0,0,0))
    for i,im in enumerate(bilder): g.paste(im,((i%2)*(W+10),(i//2)*(H+10)))
    g.save(out)
