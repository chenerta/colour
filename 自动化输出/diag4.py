# -*- coding: utf-8 -*-
"""
看看墙体填充线长什么样
"""
import fitz
from PIL import Image, ImageDraw

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]
pw, ph = page.rect.width, page.rect.height
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
iw, ih = img.size
sx, sy = iw/pw, ih/ph

draw = ImageDraw.Draw(img)

# 画所有黑色填充线段（红色）
count = 0
for p in page.get_drawings():
    fill = p.get('fill')
    if fill != (0.0, 0.0, 0.0):
        continue
    width = p.get('width', 0)
    if width != 0:
        continue
    for item in p['items']:
        if item[0] == 'l':
            x0,y0 = int(item[1].x*sx), int(item[1].y*sy)
            x1,y1 = int(item[2].x*sx), int(item[2].y*sy)
            draw.line([(x0,y0),(x1,y1)], fill='red', width=1)
            count += 1

img.save(f'{out_dir}/diag4_wall_fill.png', quality=95)
print(f'画了 {count} 条墙体填充线 → diag4_wall_fill.png')
doc.close()
