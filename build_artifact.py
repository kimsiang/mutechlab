"""Inline fonts and images as data URIs and strip the document wrapper -> single-file artifact copy."""
import base64, re, sys, pathlib
root = pathlib.Path(__file__).parent
s = (root/'index.html').read_text()
def uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode((root/path).read_bytes()).decode()
s = re.sub(r'url\((assets/fonts/[^)]+\.woff2)\)', lambda m: f'url({uri(m.group(1),"font/woff2")})', s)
s = re.sub(r'url\((assets/img/[^)]+\.webp)\)', lambda m: f'url({uri(m.group(1),"image/webp")})', s)
s = re.sub(r'poster="(assets/video/[^"]+\.webp)"', lambda m: f'poster="{uri(m.group(1),"image/webp")}"', s)
s = re.sub(r'src="(assets/img/[^"]+\.webp)"', lambda m: f'src="{uri(m.group(1),"image/webp")}"', s)
js = (root/'assets/js/hero.bundle.js').read_text().replace('</script', '<\\/script')
s = s.replace('<script type="module" src="assets/js/hero.bundle.js"></script>', '<script type="module">' + js + '</script>')
for t in ['<!doctype html>\n','<html lang="zh-CN">\n','<head>\n','<meta charset="utf-8">\n',
          '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n',
          '</head>\n','<body>\n','</body>\n','</html>\n']:
    s = s.replace(t, '', 1)
pathlib.Path(sys.argv[1]).write_text(s)
print("wrote", sys.argv[1], len(s)//1024, "KB")
