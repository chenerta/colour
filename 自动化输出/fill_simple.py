# -*- coding: utf-8 -*-
"""
1F示意图 — 最简方案
不检测墙体，直接用文字位置+合理尺寸
每个房间 = 以标签为中心的矩形，尺寸按房间类型设定
"""
import fitz
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir  = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        try: return ImageFont.truetype(fp, size)
        except: continue
    return ImageFont.load_default()

doc = fitz.open(pdf_path)
page = doc[3]
pw, ph = page.rect.width, page.rect.height
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
iw, ih = img.size
sx, sy = iw/pw, ih/ph

# 标签
blocks = page.get_text('dict')['blocks']
room_kw = ['厨房','卫生间','餐厅','庭院','花园','休闲','楼梯','酒柜',
           '客厅','卧室','书房','影音','品茶','娱乐','车库','鞋帽','衣帽']
seen = set()
labels = []
for b in blocks:
    if 'lines' not in b: continue
    for line in b['lines']:
        for span in line['spans']:
            t = span['text'].strip()
            for kw in room_kw:
                if kw in t and 'TITLE' not in t and 'PROJECT' not in t:
                    key = t[:2]
                    if key not in seen:
                        seen.add(key)
                        x0,y0,x1,y1 = span['bbox']
                        labels.append((t, (x0+x1)/2, (y0+y1)/2))
                    break

# 每个房间的尺寸（PDF坐标，单位pt）
# 格式：(宽, 高)
room_sizes = {
    '厨房':   (130, 180),
    '卫生间': (80, 80),
    '餐厅':   (150, 130),
    '庭院花园': (250, 380),
    '休闲区': (200, 300),
    '楼梯厅': (170, 120),
    '酒柜':   (60, 30),
    '客厅':   (200, 200),
    '卧室':   (180, 200),
    '书房':   (150, 150),
    '影音室': (200, 180),
    '品茶区': (150, 120),
    '娱乐区': (250, 300),
    '车库':   (300, 250),
}

# 生成房间边界
rooms = {}
for name, cx, cy in labels:
    w, h = room_sizes.get(name, (150, 150))
    x0 = cx - w/2
    y0 = cy - h/2
    x1 = cx + w/2
    y1 = cy + h/2
    
    # 确保不超出页面
    x0 = max(30, x0)
    y0 = max(30, y0)
    x1 = min(pw-30, x1)
    y1 = min(ph-30, y1)
    
    rooms[name] = (x0, y0, x1, y1)

# 解决重叠：小房间优先
def area(bbox):
    return max(0,bbox[2]-bbox[0]) * max(0,bbox[3]-bbox[1])

sorted_rooms = sorted(rooms.items(), key=lambda x: area(x[1]))

import numpy as np
GRID = 2
gw, gh = int(pw/GRID)+1, int(ph/GRID)+1
assigned = np.zeros((gh, gw), dtype=bool)

final_rooms = {}
for name, (x0,y0,x1,y1) in sorted_rooms:
    gx0 = max(0, int(x0/GRID))
    gy0 = max(0, int(y0/GRID))
    gx1 = min(gw-1, int(x1/GRID))
    gy1 = min(gh-1, int(y1/GRID))
    
    mask = np.zeros((gh, gw), dtype=bool)
    mask[gy0:gy1+1, gx0:gx1+1] = True
    mask &= ~assigned
    
    if mask.sum() > 0:
        assigned |= mask
        ys, xs = np.where(mask)
        final_rooms[name] = (xs.min()*GRID, ys.min()*GRID, (xs.max()+1)*GRID, (ys.max()+1)*GRID)

print(f"=== {len(final_rooms)} 个房间 ===")
for name, (x0,y0,x1,y1) in final_rooms.items():
    print(f"  {name}: ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) {x1-x0:.0f}x{y1-y0:.0f}")

# 画图
canvas = img.copy().convert('RGBA')
draw = ImageDraw.Draw(canvas)
font = get_font(16)

colors = [
    (255,200,200,100), (200,255,200,100), (200,200,255,100),
    (255,255,200,100), (255,200,255,100), (200,255,255,100),
    (240,220,200,100),
]

for idx, (name, (x0,y0,x1,y1)) in enumerate(final_rooms.items()):
    ix0, iy0 = int(x0*sx), int(y0*sy)
    ix1, iy1 = int(x1*sx), int(y1*sy)
    color = colors[idx % len(colors)]
    
    overlay = Image.new('RGBA', canvas.size, (0,0,0,0))
    ImageDraw.Draw(overlay).rectangle([ix0,iy0,ix1,iy1], fill=color)
    canvas = Image.alpha_composite(canvas, overlay)
    
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([ix0,iy0,ix1,iy1], outline=color[:3]+(200,), width=2)
    draw.text((ix0+5, iy0+5), name, fill=(0,0,0,255), font=font)

canvas.convert('RGB').save(f'{out_dir}/step1_simple.png', quality=95)
print(f"\n✅ step1_simple.png")
doc.close()
