"""
工序3v4：混合策略找房间边界
1. 封闭空间（厨房、卫生间、楼梯厅）→ 泛洪填充
2. 开放空间（休闲区、餐厅、庭院）→ Voronoi最近归属
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height

GRID = 3
gw = int(pw / GRID) + 1
gh = int(ph / GRID) + 1

# --- 标记墙体 ---
wall_grid = np.zeros((gh, gw), dtype=bool)
paths = page.get_drawings()
for p in paths:
    for item in p["items"]:
        if item[0] == "l":
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 5:
                steps = max(int(length / GRID), 1)
                for s in range(steps + 1):
                    t = s / max(steps, 1)
                    px = x0 + t * (x1 - x0)
                    py = y0 + t * (y1 - y0)
                    gx, gy = int(px / GRID), int(py / GRID)
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            ny, nx = gy + dy, gx + dx
                            if 0 <= ny < gh and 0 <= nx < gw:
                                wall_grid[ny][nx] = True

# --- 提取房间标签 ---
blocks = page.get_text('dict')['blocks']
room_keywords = ['厨房', '卫生间', '餐厅', '庭院', '花园', '休闲', '楼梯', '酒柜',
                 '客厅', '卧室', '书房', '影音', '品茶', '娱乐', '车库', '鞋帽', '衣帽',
                 '储藏', '设备', '手工', '琴房', '阳台', '露台', '主卫', '主卧']
seen = set()
unique_labels = []
for b in blocks:
    if 'lines' in b:
        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                for kw in room_keywords:
                    if kw in t and 'TITLE' not in t and 'PROJECT' not in t:
                        key = t[:2]
                        if key not in seen:
                            seen.add(key)
                            x0, y0, x1, y1 = span['bbox']
                            unique_labels.append((t, (x0+x1)/2, (y0+y1)/2))
                        break

# --- 泛洪填充（限定最大距离）---
def flood_fill(start_gx, start_gy, max_dist):
    visited = set()
    queue = deque()
    queue.append((start_gx, start_gy, 0))
    visited.add((start_gx, start_gy))
    
    while queue:
        x, y, dist = queue.popleft()
        if dist >= max_dist:
            continue
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < gw and 0 <= ny < gh and (nx,ny) not in visited:
                if not wall_grid[ny][nx]:
                    visited.add((nx, ny))
                    queue.append((nx, ny, dist+1))
    return visited

# --- 第一步：泛洪测试，看每个房间能扩展多大 ---
print("=== 泛洪测试（max_dist=50格=150pt）===")
room_cells = {}
for name, cx, cy in unique_labels:
    gx, gy = int(cx / GRID), int(cy / GRID)
    # 如果标签在墙上，找最近空位
    if wall_grid[gy][gx]:
        for r in range(1, 30):
            found = False
            for ddx in range(-r, r+1):
                for ddy in range(-r, r+1):
                    nx, ny = gx+ddx, gy+ddy
                    if 0 <= nx < gw and 0 <= ny < gh and not wall_grid[ny][nx]:
                        gx, gy = nx, ny
                        found = True
                        break
                if found:
                    break
            if found:
                break
    
    cells = flood_fill(gx, gy, max_dist=50)  # 150pt范围
    room_cells[name] = (gx, gy, cells)
    print(f"  {name}: 起点({gx},{gy}) 覆盖{len(cells)}网格")

# --- 第二步：区分封闭/开放房间 ---
# 封闭房间：泛洪范围小（被墙限制住了）
# 开放房间：泛洪范围大（没有足够墙体分隔）
CLOSED_THRESHOLD = 2000  # 网格数阈值

closed_rooms = {}
open_rooms = {}
for name, (gx, gy, cells) in room_cells.items():
    if len(cells) < CLOSED_THRESHOLD:
        closed_rooms[name] = cells
        print(f"  封闭: {name} ({len(cells)}网格)")
    else:
        open_rooms[name] = (gx, gy, cells)
        print(f"  开放: {name} ({len(cells)}网格)")

# --- 第三步：封闭房间直接用泛洪结果 ---
room_final = {}
for name, cells in closed_rooms.items():
    if cells:
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        room_final[name] = (min(xs)*GRID, min(ys)*GRID, (max(xs)+1)*GRID, (max(ys)+1)*GRID)

# --- 第四步：开放房间用Voronoi（只在未被封闭房间占用的区域）---
assigned_cells = set()
for name, cells in closed_rooms.items():
    assigned_cells |= cells

# 对开放区域的每个网格，找最近的开放房间标签
print("\n=== Voronoi分配开放区域 ===")
open_room_names = list(open_rooms.keys())
open_labels = {}
for name in open_room_names:
    gx, gy, _ = open_rooms[name]
    open_labels[name] = (gx, gy)

# BFS同时从所有开放房间出发
voronoi = {}
queue = deque()
for name in open_room_names:
    gx, gy, _ = open_rooms[name]
    if (gx, gy) not in assigned_cells:
        queue.append((gx, gy, name))
        voronoi[(gx, gy)] = name

while queue:
    x, y, owner = queue.popleft()
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        nx, ny = x+dx, y+dy
        if 0 <= nx < gw and 0 <= ny < gh and (nx,ny) not in assigned_cells and (nx,ny) not in voronoi:
            if not wall_grid[ny][nx]:
                voronoi[(nx, ny)] = owner
                queue.append((nx, ny, owner))

# 合并Voronoi结果
for (gx, gy), owner in voronoi.items():
    if owner not in room_final:
        room_final[owner] = (gx*GRID, gy*GRID, (gx+1)*GRID, (gy+1)*GRID)
    else:
        x0, y0, x1, y1 = room_final[owner]
        room_final[owner] = (min(x0, gx*GRID), min(y0, gy*GRID), max(x1, (gx+1)*GRID), max(y1, (gy+1)*GRID))

# --- 最终结果 ---
print("\n=== 最终房间边界 ===")
for name, bbox in room_final.items():
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    print(f"  {name}: ({bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}) 尺寸={w:.0f}x{h:.0f}")

# --- 画图 ---
img = Image.open(f'{out_dir}/1F_page4.png')
sx = img.width / pw
sy = img.height / ph
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

colors_list = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FF8800']
for i, (name, bbox) in enumerate(room_final.items()):
    ix0, iy0 = int(bbox[0]*sx), int(bbox[1]*sy)
    ix1, iy1 = int(bbox[2]*sx), int(bbox[3]*sy)
    color = colors_list[i % len(colors_list)]
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
    draw.text((ix0+3, iy0+3), name, fill=color, font=font)

out = f'{out_dir}/1F_step3v4_hybrid.png'
img.save(out)
print(f"\n输出: {out}")
doc.close()
