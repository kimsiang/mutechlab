"""Font resolver: bundled fonts/ first (works on macOS/Windows/Linux), then Linux system fonts."""
import os
from PIL import ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
CANDIDATES = {
    "zh":   [("fonts/NotoSansSC-Medium.ttf", 0), ("/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc", 0)],
    "zh_b": [("fonts/NotoSansSC-Medium.ttf", 0), ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0)],
    "en":   [("fonts/Inter.ttf", 0), ("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 0)],
    "mono": [("fonts/JetBrainsMono-Regular.ttf", 0), ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 0)],
}
def font(kind, size, weight=None):
    for rel, idx in CANDIDATES[kind]:
        p = rel if os.path.isabs(rel) else os.path.join(HERE, rel)
        if os.path.exists(p):
            f = ImageFont.truetype(p, int(size), index=idx)
            if weight is not None:
                try:
                    axes = f.get_variation_axes()
                    vals = [weight if a["name"] in (b"Weight", "Weight") else min(a["maximum"], max(a["minimum"], size)) for a in axes]
                    f.set_variation_by_axes(vals)
                except Exception: pass
            return f
    return ImageFont.load_default()
