# -*- coding: utf-8 -*-
"""
工序1：1F首层 — 识别封闭房间 + 开放空间
核心思路：泛洪先找到封闭区域，剩下连通的白色空间算作一个整体
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir  = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        try:
            return ImageFont.truetype(fp, size)
        except:
            continue
    return ImageFont.load_default()

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height

# 渲染
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
sx, sy = img.width / pw, img.height / ph

# ===== 提取房间标签 =====
blocks = page.get_text('dict')['blocks']
room_kw = ['厨房','卫生间','餐厅','庭院','花园','休闲','楼梯','酒柜',
           '客厅','卧室','书房','影音','品茶','娱乐','车库','鞋帽','衣帽','储藏','设备']
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

print(f"找到 {len(labels)} 个标签: {[l[0] for l in labels]}")

# ===== 网格化墙体 =====
GRID = 2
gw, gh = int(pw/GRID)+1, int(ph/GRID)+1
wall = np.zeros((gh, gw), dtype=bool)

for p in page.get_drawings():
    for item in p["items"]:
        if item[0] == "l":
            x0,y0 = item[1].x, item[1].y
            x1,y1 = item[2].x, item[2].y
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

print(f"网格: {gw}x{gh}, 墙体占比: {wall.sum()/(gw*gh)*100:.1f}%")

# ===== 工序1核心：从每个标签泛洪，看能到多远、能连通到谁 =====
def flood_from(gx, gy, max_dist=200):
    """从(gx,gy)泛洪，返回覆盖的网格集合"""
    visited = set()
    q = deque([(gx, gy, 0)])
    visited.add((gx, gy))
    while q:
        x, y, d = q.popleft()
        if d >= max_dist:
            continue
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if 0<=nx<gw and 0<=ny<gh and (nx,ny) not in visited and not wall[ny][nx]:
                visited.add((nx, ny))
                q.append((nx, ny, d+1))
    return visited

# 对每个标签泛洪
room_floods = {}
for name, cx, cy in labels:
    gx, gy = int(cx/GRID), int(cy/GRID)
    # 如果标签在墙上，找最近空位
    if wall[gy][gx]:
        for r in range(1, 50):
            found = False
            for ddx in range(-r, r+1):
                for ddy in range(-r, r+1):
                    nx, ny = gx+ddx, gy+ddy
                    if 0<=nx<gw and 0<=ny<gh and not wall[ny][nx]:
                        gx, gy = nx, ny
                        found = True
                        break
                if found:
                    break
            if found:
                break

    cells = flood_from(gx, gy, max_dist=200)
    room_floods[name] = cells
    print(f"  '{name}': 起点({gx},{gy}), 泛洪覆盖 {len(cells)} 格")

# ===== 分析连通性：哪些标签的泛洪区域重叠了？ =====
print("\n=== 连通性分析 ===")
names = list(room_floods.keys())
for i in range(len(names)):
    for j in range(i+1, len(names)):
        overlap = room_floods[names[i]] & room_floods[names[j]]
        if overlap:
            pct_i = len(overlap) / len(room_floods[names[i]]) * 100
            pct_j = len(overlap) / len(room_floods[names[j]]) * 100
            print(f"  {names[i]} <-> {names[j]}: 重叠 {len(overlap)} 格 ({pct_i:.0f}%/{pct_j:.0f}%)")

# ===== 工序1输出：识别封闭房间 vs 开放空间 =====
# 思路：如果两个标签的泛洪区域大面积重叠，说明它们在同一开放空间
# 先找封闭房间（泛洪面积小、不与其他标签重叠的）
# 剩下的合并为一个开放大空间

# 计算每对标签的重叠率
overlap_pairs = []
for i in range(len(names)):
    for j in range(i+1, len(names)):
        overlap = room_floods[names[i]] & room_floods[names[j]]
        if overlap:
            pct = max(len(overlap)/len(room_floods[names[i]])*100,
                      len(overlap)/len(room_floods[names[j]])*100)
            overlap_pairs.append((names[i], names[j], pct, len(overlap)))

overlap_pairs.sort(key=lambda x: -x[2])

# 封闭房间：泛洪面积较小，且不与别人大面积重叠的
closed_rooms = []
open_space_labels = []
for name in names:
    max_overlap_pct = 0
    for i_name, j_name, pct, _ in overlap_pairs:
        if name == i_name or name == j_name:
            max_overlap_pct = max(max_overlap_pct, pct)
    
    flood_area = len(room_floods[name])
    
    # 判断：面积小且重叠率低 = 封闭房间
    if flood_area < 5000 and max_overlap_pct < 50:
        closed_rooms.append(name)
    else:
        open_space_labels.append(name)

print(f"\n=== 封闭房间: {closed_rooms}")
print(f"=== 开放空间: {open_space_labels}")

# ===== 确定每个空间的精确边界 =====
# 封闭房间：直接用泛洪区域的bbox
# 开放空间：合并所有相关标签的泛洪区域

spaces = {}

# 封闭房间
for name in closed_rooms:
    cells = room_floods[name]
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    bbox = (min(xs)*GRID, min(ys)*GRID, (max(xs)+1)*GRID, (max(ys)+1)*GRID)
    spaces[name] = {'bbox': bbox, 'type': 'closed', 'labels': [name]}

# 开放空间
if open_space_labels:
    all_cells = set()
    for name in open_space_labels:
        all_cells |= room_floods[name]
    xs = [c[0] for c in all_cells]
    ys = [c[1] for c in all_cells]
    bbox = (min(xs)*GRID, min(ys)*GRID, (max(xs)+1)*GRID, (max(ys)+1)*GRID)
    open_name = '+'.join(open_space_labels)
    spaces[open_name] = {'bbox': bbox, 'type': 'open', 'labels': open_space_labels}

print(f"\n=== 最终空间划分 ===")
for name, info in spaces.items():
    x0,y0,x1,y1 = info['bbox']
    print(f"  {name}: ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) {x1-x0:.0f}x{y1-y0:.0f} [{info['type']}]")

# ===== 工序1验证：在图上画出空间边界 =====
img1 = img.copy()
draw = ImageDraw.Draw(img1)
font = get_font(18)

for name, info in spaces.items():
    x0, y0, x1, y1 = info['bbox']
    ix0, iy0 = int(x0*sx), int(y0*sy)
    ix1, iy1 = int(x1*sx), int(y1*sy)
    
    if info['type'] == 'closed':
        color = (0, 200, 0)  # 绿色=封闭房间
    else:
        color = (0, 100, 255)  # 蓝色=开放空间
    
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
    draw.text((ix0+5, iy0+5), name, fill=color, font=font)

img1.save(f'{out_dir}/step1_spaces.png', quality=95)
print(f"\n✅ 工序1验证图: step1_spaces.png")
print("   绿框=封闭房间, 蓝框=开放空间")

doc.close()
