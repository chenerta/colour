"""
工序3v3：网格化泛洪填充找房间边界
1. 把PDF页面分成5pt分辨率的网格
2. 标记靠近线段的网格为"墙"
3. 从每个房间标签向外泛洪，确定房间范围
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height
print(f"PDF页面: {pw:.0f}x{ph:.0f}")

# --- 网格分辨率 ---
GRID = 3  # 每3pt一个网格
gw = int(pw / GRID) + 1
gh = int(ph / GRID) + 1
print(f"网格: {gw}x{gh}")

# --- 标记墙体网格 ---
wall_grid = np.zeros((gh, gw), dtype=bool)

paths = page.get_drawings()
wall_lines = []
for p in paths:
    for item in p["items"]:
        if item[0] == "l":
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 5:
                wall_lines.append((x0, y0, x1, y1))
                # 标记线段经过的网格
                steps = max(int(length / GRID), 1)
                for s in range(steps + 1):
                    t = s / max(steps, 1)
                    px = x0 + t * (x1 - x0)
                    py = y0 + t * (y1 - y0)
                    gx, gy = int(px / GRID), int(py / GRID)
                    if 0 <= gx < gw and 0 <= gy < gh:
                        # 标记周围3x3网格为墙（线段有粗细）
                        for dy in range(-1, 2):
                            for dx in range(-1, 2):
                                ny, nx = gy + dy, gx + dx
                                if 0 <= ny < gh and 0 <= nx < gw:
                                    wall_grid[ny][nx] = True

print(f"墙体线段数: {len(wall_lines)}")
print(f"墙体网格数: {wall_grid.sum()} / {gw*gh} ({wall_grid.sum()/(gw*gh)*100:.1f}%)")

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

# --- 泛洪填充 ---
from collections import deque

def flood_fill(start_gx, start_gy, max_dist=120):
    """从起点泛洪，返回覆盖的网格范围（不穿越墙体）"""
    visited = set()
    queue = deque()
    queue.append((start_gx, start_gy, 0))
    visited.add((start_gx, start_gy))
    
    min_gx, max_gx = start_gx, start_gx
    min_gy, max_gy = start_gy, start_gy
    
    while queue:
        x, y, dist = queue.popleft()
        if dist > max_dist:
            continue
        
        min_gx = min(min_gx, x)
        max_gx = max(max_gx, x)
        min_gy = min(min_gy, y)
        max_gy = max(max_gy, y)
        
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < gw and 0 <= ny < gh and (nx,ny) not in visited:
                if not wall_grid[ny][nx]:  # 不是墙
                    visited.add((nx, ny))
                    queue.append((nx, ny, dist+1))
    
    return min_gx, min_gy, max_gx, max_gy, visited

print("\n=== 泛洪填充找房间边界 ===")
room_results = {}
all_visited = {}  # 记录每个房间覆盖的网格

for name, cx, cy in unique_labels:
    gx, gy = int(cx / GRID), int(cy / GRID)
    if wall_grid[gy][gx]:
        # 标签在墙体上，向外找一个空位
        for r in range(1, 20):
            found = False
            for dx in range(-r, r+1):
                for dy in range(-r, r+1):
                    nx, ny = gx+dx, gy+dy
                    if 0 <= nx < gw and 0 <= ny < gh and not wall_grid[ny][nx]:
                        gx, gy = nx, ny
                        found = True
                        break
                if found:
                    break
            if found:
                break
    
    min_gx, min_gy, max_gx, max_gy, visited = flood_fill(gx, gy, max_dist=150)
    
    # 转回PDF坐标
    x0 = min_gx * GRID
    y0 = min_gy * GRID
    x1 = (max_gx + 1) * GRID
    y1 = (max_gy + 1) * GRID
    
    room_results[name] = (x0, y0, x1, y1)
    all_visited[name] = visited
    
    w, h = x1-x0, y1-y0
    print(f"  {name}: PDF({cx:.0f},{cy:.0f}) 网格({gx},{gy}) 边界=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) 尺寸={w:.0f}x{h:.0f} 覆盖网格={len(visited)}")

# --- 解决重叠（小房间优先）---
def area(bbox):
    return max(0, bbox[2]-bbox[0]) * max(0, bbox[3]-bbox[1])

# 按面积从小到大排序
sorted_rooms = sorted(room_results.items(), key=lambda x: area(x[1]))

# 用网格级别的去重：已经被分配的网格不能被其他房间占用
assigned = set()
room_final = {}

for name, bbox in sorted_rooms:
    visited = all_visited[name]
    # 只保留未被分配的网格
    my_cells = visited - assigned
    assigned |= my_cells
    
    if my_cells:
        xs = [c[0] for c in my_cells]
        ys = [c[1] for c in my_cells]
        x0 = min(xs) * GRID
        y0 = min(ys) * GRID
        x1 = (max(xs) + 1) * GRID
        y1 = (max(ys) + 1) * GRID
        room_final[name] = (x0, y0, x1, y1)
    else:
        room_final[name] = bbox  # 兜底

print("\n=== 最终边界（去重后）===")
for name, bbox in room_final.items():
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    print(f"  {name}: ({bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}) 尺寸={w:.0f}x{h:.0f}")

# --- 画图验证 ---
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

out = f'{out_dir}/1F_step3v3_flood.png'
img.save(out)
print(f"\n输出: {out}")
doc.close()
