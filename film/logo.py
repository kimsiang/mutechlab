"""Wordmark for 缪子科技实验室.

If a real logo file exists (logo.png / logo.svg converted to png) it is used as-is;
otherwise a typeset placeholder wordmark is generated in the GSCAN-like
navy-on-transparent style.  Returns an RGBA PIL image.
"""
import os
from PIL import Image, ImageDraw, ImageFont

NAVY = (22, 28, 168, 255)          # #161CA8, close to the GSCAN blue
from fonts_rt import font as rt_font

def load_logo(custom="logo.png"):
    if os.path.exists(custom):
        return Image.open(custom).convert("RGBA")
    return make_placeholder()

def make_placeholder(W=1800, H=520):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1 = rt_font("zh_b", 250)
    f2 = rt_font("en", 54, 600)
    t1 = "缪子科技实验室"
    bb = d.textbbox((0, 0), t1, font=f1)
    w1 = bb[2] - bb[0]; h1 = bb[3] - bb[1]
    x = (W - w1) // 2 - bb[0]; y = 40 - bb[1]
    d.text((x, y), t1, font=f1, fill=NAVY)
    t2 = "M U O N   T E C H   L A B"
    bb2 = d.textbbox((0, 0), t2, font=f2)
    w2 = bb2[2] - bb2[0]
    d.text(((W - w2) // 2 - bb2[0], 40 + h1 + 60 - bb2[1]), t2, font=f2, fill=NAVY)
    # thin rule between the two lines
    d.rectangle([(W - w1) // 2, 40 + h1 + 34, (W + w1) // 2, 40 + h1 + 38], fill=NAVY)
    return img

if __name__ == "__main__":
    make_placeholder().save("logo_placeholder.png")
    print("wrote logo_placeholder.png")
