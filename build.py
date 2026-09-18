#!/usr/bin/env python3
"""构建：把 data/passages.json 注入模板，可选地切字体子集，生成 dist/index.html。

  python3 build.py            生成 dist/index.html + dist/fonts/feng.woff2（字体另存，适合部署）
  python3 build.py --inline   字体以 data URI 内嵌，生成真正的单文件（适合发给别人）

字体：把 LXGW WenKai（霞鹜文楷，OFL）的 Light 版放到 fonts/LXGWWenKai-Light.ttf
      （https://github.com/lxgw/LxgwWenKai/releases）。找不到就退回 Google Fonts。
      子集只含全部段落用到的字，每次 build 重新切，加字不用管。

序列：east 与 west 按 3:2 交错；带 season 的段落只在对应季节出现（运行时按日期筛池）。
"""
import base64, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INLINE = "--inline" in sys.argv
FONT_SRC = ROOT / "fonts" / "LXGWWenKai-Light.ttf"

# ---- 文本 ----
data = json.loads((ROOT / "data" / "passages.json").read_text(encoding="utf-8"))
east, west = data["east"], data["west"]
seq, i, j = [], 0, 0
while i < len(east) or j < len(west):
    for _ in range(3):
        if i < len(east): seq.append(east[i]); i += 1
    for _ in range(2):
        if j < len(west): seq.append(west[j]); j += 1
payload = json.dumps(seq, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

html = (ROOT / "src" / "index.html").read_text(encoding="utf-8").replace("/*PASSAGES*/", payload, 1)
dist = ROOT / "dist"; dist.mkdir(exist_ok=True)

# ---- 字体 ----
def subset_font() -> Path | None:
    if not FONT_SRC.exists():
        return None
    chars = set()
    for p in seq:
        for k in ("t", "s", "n", "o"):
            chars.update(p.get(k, ""))
    chars.update("〇一二三四五六七八九十年月日风昨今声试译。，、；：？！「」『』《》〈〉……—–·（）请开启")
    chars.update(chr(c) for c in range(0x20, 0x7F))
    txt = dist / "_subset.txt"
    txt.write_text("".join(sorted(chars)), encoding="utf-8")
    out = dist / "fonts" / "feng.woff2"; out.parent.mkdir(exist_ok=True)
    r = subprocess.run(["pyftsubset", str(FONT_SRC), f"--text-file={txt}", "--flavor=woff2",
                        "--layout-features+=vert,vrt2,locl", f"--output-file={out}",
                        "--no-hinting", "--desubroutinize"], capture_output=True, text=True)
    txt.unlink(missing_ok=True)
    if r.returncode != 0:
        print("字体子集失败：", r.stderr.strip()[-200:]); return None
    return out

woff = subset_font()
if woff:
    if INLINE:
        src = "data:font/woff2;base64," + base64.b64encode(woff.read_bytes()).decode()
    else:
        src = "fonts/feng.woff2"
    fontface = ('@font-face { font-family: "Feng"; src: url(' + src + ') format("woff2"); '
                'font-weight: 300; font-display: swap; }')
    html = (html.replace("<!--FONTLINK-->", "")
                .replace("/*FONTFACE*/", fontface)
                .replace('/*SERIF*/', '"Feng", ')
                .replace('/*BRUSH*/', '"Feng", ')
                .replace('/*LATIN*/', '"Feng", '))
    note = f"字体 {woff.stat().st_size // 1024} KB（{'内嵌' if INLINE else '外链'}）"
else:
    link = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400'
            '&family=Noto+Serif:ital,wght@0,300;1,300&family=Ma+Shan+Zheng&display=swap" rel="stylesheet">')
    html = (html.replace("<!--FONTLINK-->", link).replace("/*FONTFACE*/", "")
                .replace('/*SERIF*/', '').replace('/*BRUSH*/', '').replace('/*LATIN*/', ''))
    note = "未找到 fonts/LXGWWenKai-Light.ttf，退回 Google Fonts"

out = dist / "index.html"
out.write_text(html, encoding="utf-8")
print(f"{len(east)} east + {len(west)} west = {len(seq)} 段 → {out.relative_to(ROOT)} "
      f"({out.stat().st_size // 1024} KB)；{note}")
