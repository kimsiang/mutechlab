"""Rebuild the logo crisply at ~5x: trace the mark (left ~70 px) with potrace after a
smoothing upscale; re-typeset the two text lines in matching fonts and the logo's own colours."""
import numpy as np, potrace
from PIL import Image, ImageDraw, ImageFont
src=Image.open("logo_src.png").convert("RGBA")
a=np.asarray(src).astype(float); rgb=a[...,:3]; al=a[...,3]/255
ink=np.clip((255-rgb.min(axis=2))/255,0,1)*al; b=rgb[...,2]; r=rgb[...,0]
dark_px=(ink>0.45)&(b<120); light_px=(ink>0.35)&(b>=120)&(b>r+40)
NAVY=tuple(int(v) for v in rgb[dark_px].mean(axis=0))+(255,)
BLUE=tuple(int(v) for v in rgb[light_px].mean(axis=0))+(255,)
# ---- mark: columns 0..MARKW of the source
cols=np.where(ink.max(axis=0)>0.3)[0]; gaps=np.where(np.diff(cols)>4)[0]; MARKW=int(cols[gaps[0]])+2
U=8; S=10  # U: pre-smoothing upscale for tracing, S: trace coordinate scale
from PIL import ImageFilter
def soft(mask):
    m=Image.fromarray((mask*255).astype(np.uint8)).resize((src.width*U, src.height*U), Image.BICUBIC).filter(ImageFilter.GaussianBlur(U*0.45))
    return np.asarray(m)>127
W,H=src.width*S, src.height*S
out=Image.new("RGBA",(W,H),(0,0,0,0))
def fill(mask,col):
    path=potrace.Bitmap(~mask).trace(turdsize=8, alphamax=1.3, opttolerance=0.4)
    acc=np.zeros((H,W),bool); k=S/U
    for curve in path:
        pts=[(curve.start_point.x*k,curve.start_point.y*k)]
        for seg in curve:
            if seg.is_corner: pts+=[(seg.c.x*k,seg.c.y*k),(seg.end_point.x*k,seg.end_point.y*k)]
            else:
                p0=pts[-1]; c1=(seg.c1.x*k,seg.c1.y*k); c2=(seg.c2.x*k,seg.c2.y*k); p3=(seg.end_point.x*k,seg.end_point.y*k)
                for t in np.linspace(0,1,12)[1:]:
                    pts.append(((1-t)**3*p0[0]+3*(1-t)**2*t*c1[0]+3*(1-t)*t**2*c2[0]+t**3*p3[0],(1-t)**3*p0[1]+3*(1-t)**2*t*c1[1]+3*(1-t)*t**2*c2[1]+t**3*p3[1]))
        m=Image.new("1",(W,H),0); ImageDraw.Draw(m).polygon(pts, fill=1); acc^=np.asarray(m)
    layer=Image.new("RGBA",(W,H),col); layer.putalpha(Image.fromarray((acc*255).astype(np.uint8))); out.alpha_composite(layer)
keep=np.zeros_like(dark_px); keep[:, :MARKW]=True
fill(soft(dark_px&keep), NAVY); fill(soft(light_px&keep), BLUE)
# ---- text: measure source text rows
rows=np.where((ink[:, MARKW:]>0.3).any(axis=1))[0]; rg=np.where(np.diff(rows)>2)[0]
cn_rows=(rows[0], rows[rg[0]]); en_rows=(rows[rg[0]+1], rows[-1])
tx=int(cols[gaps[0]+1])*S
d=ImageDraw.Draw(out)
def fit(font_path, text, target_h, idx=0):
    lo,hi=10,1200
    while hi-lo>1:
        mid=(lo+hi)//2; f=ImageFont.truetype(font_path, mid, index=idx); bb=d.textbbox((0,0),text,font=f)
        (lo,hi)=(mid,hi) if bb[3]-bb[1] < target_h else (lo,mid)
    return ImageFont.truetype(font_path, lo, index=idx)
cn="缪子科技实验室"; en="Muon Tech Lab"
f_cn=fit("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", cn, (cn_rows[1]-cn_rows[0]+1)*S)
f_en=fit("/usr/share/fonts/opentype/inter/Inter-Regular.otf", en, (en_rows[1]-en_rows[0]+1)*S*1.12)
for text,f,row in ((cn,f_cn,cn_rows),(en,f_en,en_rows)):
    bb=d.textbbox((0,0),text,font=f); d.text((tx-bb[0], row[0]*S-bb[1] - (0 if text==cn else 0)), text, font=f, fill=NAVY)
# crop + 5x
bbox=out.getbbox(); out=out.crop(bbox)
out=out.resize((out.width//2,out.height//2), Image.LANCZOS); out.save("logo.png"); print(out.size, NAVY, BLUE, MARKW)
