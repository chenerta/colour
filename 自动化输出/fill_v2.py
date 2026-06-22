# -*- coding: utf-8 -*-
"""
1F示意图 — 只用粗线条（宽度>=0.72）作为墙体
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
page = doc[3]
pw, ph = page.rect.width, page.rect.height
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
iw, ih = img.size

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

# 墙体网格 — 只用粗线条
GRID = 2
gw, gh = int(pw/GRID)+1, int(ph/GRID)+1
wall = np.zeros((gh, gw), dtype=bool)
wall_count = 0

for p in page.get_drawings():
    w = p.get('width', 0)
    if w < 0.72:  # 只用粗线条（墙体）
        continue
    for item in p["items"]:
        if item[0] == "l":
            x0,y0,x1,y1 = item[1].x, item[1].y, item[2].x, item[2].y
            L = ((x1-x0)**2+(y1-y0)**2)**0.5
            if L > 10:  # 短线也过滤掉
                wall_count += 1
                steps = max(int(L/GRID),1)
                for s in range(steps+1):
                    t = s/max(steps,1)
                    px,py = x0+t*(x1-x0), y0+t*(y1-y0)
                    gx,gy = int(px/GRID), int(py/GRID)
                    # 膨胀1格（墙有一定厚度）
                    for dy in range(-1,2):
                        for dx in range(-1,2):
                            ny,nx = gy+dy, gx+dx
                            if 0<=ny<gh and 0<=nx<gw:
                                wall[ny][nx] = True

print(f"粗线条(>=0.72): {wall_count} 条")
print(f"网格: {gw}x{gh}, 墙体占比: {wall.sum()/(gw*gh)*100:.1f}%")

# 泛洪
def flood(gx, gy, max_d=300):
    vis = np.zeros((gh, gw), dtype=bool)
    q = deque([(gx,gy,0)])
    vis[gy][gx] = True
    while q:
        x,y,d = q.popleft()
        if d >= max_d: continue
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx,ny = x+dx, y+dy
            if 0<=nx<gw and 0<=ny<gh and not vis[ny][nx] and not wall[ny][nx]:
                vis[ny][nx] = True
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
                        gx,gy = nx,ny; found=True; break
                if found: break
            if found: break
    floods[name] = flood(gx, gy)
    print(f"  '{name}': {floods[name].sum()} 格")

# 合并连通空间
names = list(floods.keys())
parent = {n:n for n in names}
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    ra,rb = find(a),find(b)
    if ra!=rb: parent[ra]=rb

for i in range(len(names)):
    for j in range(i+1, len(names)):
        if (floods[names[i]] & floods[names[j]]).sum() > 50:
            union(names[i], names[j])

groups = {}
for n in names:
    r = find(n)
    if r not in groups: groups[r] = []
    groups[r].append(n)

print(f"\n=== {len(groups)} 个空间 ===")
for root, members in groups.items():
    merged = np.zeros((gh,gw), dtype=bool)
    for m in members: merged |= floods[m]
    print(f"  {'+'.join(members)}: {merged.sum()} 格")

# 画图
space_id = np.zeros((gh, gw), dtype=np.int32)
for idx, (root, members) in enumerate(groups.items()):
    for m in members:
        space_id[floods[m]] = idx + 1

space_img = Image.fromarray(space_id.astype(np.uint8), mode='L')
space_img = space_img.resize((iw, ih), Image.NEAREST)

palette = [
    (0, 0, 0),
    (255, 200, 200),
    (200, 255, 200),
    (200, 200, 255),
    (255, 255, 200),
    (255, 200, 255),
    (200, 255, 255),
    (240, 220, 200),
]

overlay_arr = np.zeros((ih, iw, 4), dtype=np.uint8)
space_arr = np.array(space_img)
for sid in range(1, len(groups)+1):
    mask = space_arr == sid
    r,g,b = palette[sid] if sid < len(palette) else (200,200,200)
    overlay_arr[mask] = [r, g, b, 100]

overlay = Image.fromarray(overlay_arr, mode='RGBA')
canvas = Image.alpha_composite(img.convert('RGBA'), overlay)

draw = ImageDraw.Draw(canvas)
font = get_font(18)
for idx, (root, members) in enumerate(groups.items()):
    merged = np.zeros((gh,gw), dtype=bool)
    for m in members: merged |= floods[m]
    ys, xs = np.where(merged)
    if len(xs)==0: continue
    ix0 = int(xs.min()*GRID/pw*iw)
    iy0 = int(ys.min()*GRID/ph*ih)
    ix1 = int((xs.max()+1)*GRID/pw*iw)
    iy1 = int((ys.max()+1)*GRID/ph*ih)
    color = palette[idx+1] if idx+1 < len(palette) else (200,200,200)
    draw.rectangle([ix0,iy0,ix1,iy1], outline=color+(255,), width=3)
    draw.text((ix0+5, iy0+5), '+'.join(members), fill=color+(255,), font=font)

canvas.convert('RGB').save(f'{out_dir}/step1_final.png', quality=95)
print(f"\n✅ step1_final.png")
doc.close()
