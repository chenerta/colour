# -*- coding: utf-8 -*-
"""
1F首层示意图 —— 只做边界+涂色
思路：
1. 网格化墙体
2. 从每个标签泛洪
3. 泛洪重叠的标签 = 同一空间，合并
4. 每个空间涂一个颜色
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir  = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        try: return ImageFont.truetype(fp, size)
        except: continue
    return ImageFont.load_default()

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height

mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
sx, sy = img.width / pw, img.height / ph

# ===== 标签 =====
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

# ===== 墙体网格 =====
GRID = 2
gw, gh = int(pw/GRID)+1, int(ph/GRID)+1
wall = np.zeros((gh, gw), dtype=bool)
for p in page.get_drawings():
    for item in p["items"]:
        if item[0] == "l":
            x0,y0,x1,y1 = item[1].x, item[1].y, item[2].x, item[2].y
            L = ((x1-x0)**2+(y1-y0)**2)**0.5
            if L > 3:
                steps = max(int(L/GRID),1)
                for s in range(steps+1):
                    t = s/max(steps,1)
                    px,py = x0+t*(x1-x0), y0+t*(y1-y0)
                    gx,gy = int(px/GRID), int(py/GRID)
                    for dy in range(-1,2):
                        for dx in range(-1,2):
                            ny,nx = gy+dy, gx+dx
                            if 0<=ny<gh and 0<=nx<gw:
                                wall[ny][nx] = True

# ===== 泛洪 =====
def flood(gx, gy, max_d=300):
    vis = set()
    q = deque([(gx,gy,0)])
    vis.add((gx,gy))
    while q:
        x,y,d = q.popleft()
        if d >= max_d: continue
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx,ny = x+dx, y+dy
            if 0<=nx<gw and 0<=ny<gh and (nx,ny) not in vis and not wall[ny][nx]:
                vis.add((nx,ny))
                q.append((nx,ny,d+1))
    return vis

floods = {}
for name, cx, cy in labels:
    gx, gy = int(cx/GRID), int(cy/GRID)
    if wall[gy][gx]:
        for r in range(1,50):
            found = False
            for ddx in range(-r,r+1):
                for ddy in range(-r,r+1):
                    nx,ny = gx+ddx,gy+ddy
                    if 0<=nx<gw and 0<=ny<gh and not wall[ny][nx]:
                        gx,gy = nx,ny; found = True; break
                if found: break
            if found: break
    floods[name] = flood(gx, gy)
    print(f"  '{name}': {len(floods[name])} 格")

# ===== 合并连通空间 =====
names = list(floods.keys())
parent = {n: n for n in names}
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb

for i in range(len(names)):
    for j in range(i+1, len(names)):
        overlap = len(floods[names[i]] & floods[names[j]])
        if overlap > 100:  # 重叠超过100格 = 连通
            union(names[i], names[j])

groups = {}
for n in names:
    r = find(n)
    if r not in groups: groups[r] = []
    groups[r].append(n)

print(f"\n=== {len(groups)} 个独立空间 ===")
for root, members in groups.items():
    merged = set()
    for m in members: merged |= floods[m]
    print(f"  {members}: {len(merged)} 格")

# ===== 画图：每个空间一个颜色 =====
colors = [
    (255, 200, 200, 120),  # 浅红
    (200, 255, 200, 120),  # 浅绿
    (200, 200, 255, 120),  # 浅蓝
    (255, 255, 200, 120),  # 浅黄
    (255, 200, 255, 120),  # 浅紫
    (200, 255, 255, 120),  # 浅青
    (240, 220, 200, 120),  # 浅橙
]

# 创建RGBA画布
canvas = img.copy().convert('RGBA')
overlay = Image.new('RGBA', canvas.size, (0,0,0,0))
ox, oy = canvas.size

for idx, (root, members) in enumerate(groups.items()):
    merged = set()
    for m in members: merged |= floods[m]
    
    color = colors[idx % len(colors)]
    
    # 把泛洪区域画到overlay上
    for gx, gy in merged:
        px0, py0 = gx * GRID, gy * GRID
        # 转图片坐标
        ix0 = int(px0 * sx / GRID) * GRID  # 不对，直接转换
        # 简单方法：每个网格对应一个像素块
        ix = int(gx * GRID * sx / pw * ox / ox)  # 这样不对
        # 直接用比例
        ix = int(gx * GRID / pw * ox)
        iy = int(gy * GRID / ph * oy)
        if 0 <= ix < ox and 0 <= iy < oy:
            overlay.putpixel((ix, iy), color)

canvas = Image.alpha_composite(canvas, overlay)

# 画边界框
draw = ImageDraw.Draw(canvas)
font = get_font(18)
for idx, (root, members) in enumerate(groups.items()):
    merged = set()
    for m in members: merged |= floods[m]
    xs = [c[0] for c in merged]
    ys = [c[1] for c in merged]
    ix0, iy0 = int(min(xs)*GRID*sx), int(min(ys)*GRID*sy)
    ix1, iy1 = int((max(xs)+1)*GRID*sx), int((max(ys)+1)*GRID*sy)
    color_rgb = colors[idx % len(colors)][:3]
    draw.rectangle([ix0,iy0,ix1,iy1], outline=color_rgb+(255,), width=3)
    label = '+'.join(members)
    draw.text((ix0+5, iy0+5), label, fill=color_rgb+(255,), font=font)

result = canvas.convert('RGB')
result.save(f'{out_dir}/step1_fill.png', quality=95)
print(f"\n✅ step1_fill.png")
doc.close()
