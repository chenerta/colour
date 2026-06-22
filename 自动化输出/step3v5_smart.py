"""
工序3v5：用PDF文字+墙体做"合理边界"
核心思路：不靠泛洪，不靠Voronoi
而是对每个房间，从标签位置向外搜索，找最远的合理墙体作为边界
"合理" = 不超过200pt，且形成的矩形面积在合理范围内
"""
import fitz
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height

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

# --- 提取墙体线段 ---
paths = page.get_drawings()
h_walls = []  # (x0, y, x1)
v_walls = []  # (y0, x, y1)
for p in paths:
    for item in p["items"]:
        if item[0] == "l":
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 15:
                if abs(y0 - y1) < 3:
                    h_walls.append((min(x0,x1), y0, max(x0,x1)))
                elif abs(x0 - x1) < 3:
                    v_walls.append((x0, min(y0,y1), max(y0,y1)))

print(f"水平墙: {len(h_walls)}, 垂直墙: {len(v_walls)}")

# --- 对每个房间找所有方向的墙 ---
def find_all_walls(walls, direction, cx, cy, is_h=True, max_dist=200):
    """找某个方向上的所有墙，按距离排序"""
    results = []
    if is_h:
        for wx0, wy, wx1 in walls:
            if wx0 - 20 <= cx <= wx1 + 20:
                if direction == 'up' and wy < cy:
                    d = cy - wy
                    if 5 < d < max_dist:
                        results.append((d, wy))
                elif direction == 'down' and wy > cy:
                    d = wy - cy
                    if 5 < d < max_dist:
                        results.append((d, wy))
    else:
        for wx, wy0, wy1 in walls:
            if wy0 - 20 <= cy <= wy1 + 20:
                if direction == 'left' and wx < cx:
                    d = cx - wx
                    if 5 < d < max_dist:
                        results.append((d, wx))
                elif direction == 'right' and wx > cx:
                    d = wx - cx
                    if 5 < d < max_dist:
                        results.append((d, wx))
    results.sort()
    return results

# --- 为每个房间选择最佳边界 ---
print("\n=== 每个房间的候选墙 ===")
room_boundaries = {}

for name, cx, cy in unique_labels:
    up_walls = find_all_walls(h_walls, 'up', cx, cy, True)
    down_walls = find_all_walls(h_walls, 'down', cx, cy, True)
    left_walls = find_all_walls(v_walls, 'left', cx, cy, False)
    right_walls = find_all_walls(v_walls, 'right', cx, cy, False)
    
    print(f"\n  {name} (中心: {cx:.0f},{cy:.0f}):")
    print(f"    上方墙: {[(f'{d:.0f}@{w:.0f}') for d,w in up_walls[:5]]}")
    print(f"    下方墙: {[(f'{d:.0f}@{w:.0f}') for d,w in down_walls[:5]]}")
    print(f"    左方墙: {[(f'{d:.0f}@{w:.0f}') for d,w in left_walls[:5]]}")
    print(f"    右方墙: {[(f'{d:.0f}@{w:.0f}') for d,w in right_walls[:5]]}")
    
    # 选择策略：找最远的墙（房间边界通常是外围的墙）
    # 但如果最远的墙太远（>150），就用第二远的
    def pick_wall(wall_list, prefer='far'):
        if not wall_list:
            return None
        if prefer == 'far':
            # 从最远开始，找一个合理的
            for d, w in reversed(wall_list):
                if d > 40:  # 至少40pt
                    return w
            return wall_list[-1][1]  # 最远的
        else:
            return wall_list[0][1]  # 最近的
    
    # 封闭小房间用最近墙，开放大房间用最远墙
    is_small = any(kw in name for kw in ['卫生间', '酒柜', '楼梯', '鞋帽', '储藏'])
    prefer = 'near' if is_small else 'far'
    
    up = pick_wall(up_walls, prefer)
    down = pick_wall(down_walls, prefer)
    left = pick_wall(left_walls, prefer)
    right = pick_wall(right_walls, prefer)
    
    if up is None: up = cy - 100
    if down is None: down = cy + 100
    if left is None: left = cx - 100
    if right is None: right = cx + 100
    
    margin = 8
    x0 = min(left, right) + margin
    y0 = min(up, down) + margin
    x1 = max(left, right) - margin
    y1 = max(up, down) - margin
    
    room_boundaries[name] = (x0, y0, x1, y1)
    print(f"    → 边界: ({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) 尺寸={x1-x0:.0f}x{y1-y0:.0f}")

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
for i, (name, bbox) in enumerate(room_boundaries.items()):
    ix0, iy0 = int(bbox[0]*sx), int(bbox[1]*sy)
    ix1, iy1 = int(bbox[2]*sx), int(bbox[3]*sy)
    color = colors_list[i % len(colors_list)]
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
    draw.text((ix0+3, iy0+3), name, fill=color, font=font)

out = f'{out_dir}/1F_step3v5_smart.png'
img.save(out)
print(f"\n输出: {out}")
doc.close()
