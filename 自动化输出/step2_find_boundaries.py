"""
工序2：从PDF墙体线条推算每个房间的边界
方法：以房间标签为中心，向四个方向搜索最近的墙体线条
"""
import fitz
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F

# --- 提取房间标签 ---
blocks = page.get_text('dict')['blocks']
room_keywords = ['厨房', '卫生间', '餐厅', '庭院', '花园', '休闲', '楼梯', '酒柜',
                 '客厅', '卧室', '书房', '影音', '品茶', '娱乐', '车库', '鞋帽', '衣帽',
                 '储藏', '设备', '手工', '琴房', '阳台', '露台', '主卫', '主卧']
room_labels = []
for b in blocks:
    if 'lines' in b:
        for line in b['lines']:
            for span in line['spans']:
                t = span['text'].strip()
                for kw in room_keywords:
                    if kw in t and 'TITLE' not in t and 'PROJECT' not in t:
                        x0, y0, x1, y1 = span['bbox']
                        room_labels.append((t, (x0+x1)/2, (y0+y1)/2))
                        break

# 去重（中文+英文可能匹配两次）
seen = set()
unique_labels = []
for name, cx, cy in room_labels:
    key = name[:2]  # 用前两个字去重
    if key not in seen:
        seen.add(key)
        unique_labels.append((name, cx, cy))

# --- 提取墙体线条 ---
paths = page.get_drawings()
h_walls = []  # 水平墙 (y固定, x范围)
v_walls = []  # 垂直墙 (x固定, y范围)

for p in paths:
    for item in p["items"]:
        if item[0] == "l":
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 20:
                if abs(y0 - y1) < 3:  # 水平
                    h_walls.append((min(x0,x1), y0, max(x0,x1), y0))
                elif abs(x0 - x1) < 3:  # 垂直
                    v_walls.append((x0, min(y0,y1), x0, max(y0,y1)))

print(f"水平墙线: {len(h_walls)}, 垂直墙线: {len(v_walls)}")

# --- 为每个房间找边界 ---
def find_nearest_wall(walls, direction, cx, cy, is_horizontal=True):
    """从(cx,cy)向direction方向找最近的墙线
    direction: 'up'(-y), 'down'(+y), 'left'(-x), 'right'(+x)
    """
    best = None
    best_dist = 9999
    
    if is_horizontal:
        # 水平墙线，找在cx附近的，且在cy的direction方向
        for wx0, wy, wx1, wy1 in walls:
            # 墙线要在cx附近（覆盖cx或距离<20）
            if wx0 - 10 <= cx <= wx1 + 10:
                if direction == 'up' and wy < cy:
                    dist = cy - wy
                    if dist < best_dist:
                        best_dist = dist
                        best = wy
                elif direction == 'down' and wy > cy:
                    dist = wy - cy
                    if dist < best_dist:
                        best_dist = dist
                        best = wy
    else:
        # 垂直墙线，找在cy附近的，且在cx的direction方向
        for wx, wy0, wx1, wy1 in walls:
            if wy0 - 10 <= cy <= wy1 + 10:
                if direction == 'left' and wx < cx:
                    dist = cx - wx
                    if dist < best_dist:
                        best_dist = dist
                        best = wx
                elif direction == 'right' and wx > cx:
                    dist = wx - cx
                    if dist < best_dist:
                        best_dist = dist
                        best = wx
    return best, best_dist

# 计算每个房间的边界
print("\n=== 房间边界计算 ===")
room_boundaries = {}
for name, cx, cy in unique_labels:
    wall_up, d_up = find_nearest_wall(h_walls, 'up', cx, cy, True)
    wall_down, d_down = find_nearest_wall(h_walls, 'down', cx, cy, True)
    wall_left, d_left = find_nearest_wall(v_walls, 'left', cx, cy, False)
    wall_right, d_right = find_nearest_wall(v_walls, 'right', cx, cy, False)
    
    # 如果某方向找不到墙，用默认距离
    margin = 15
    if wall_up is None: wall_up = cy - 60
    if wall_down is None: wall_down = cy + 60
    if wall_left is None: wall_left = cx - 60
    if wall_right is None: wall_right = cx + 60
    
    bbox = (wall_left + margin, wall_up + margin, wall_right - margin, wall_down - margin)
    room_boundaries[name] = bbox
    print(f"  {name}: PDF({cx:.0f},{cy:.0f}) 边界=({bbox[0]:.0f},{bbox[1]:.0f},{bbox[2]:.0f},{bbox[3]:.0f}) 距离: 上{d_up:.0f} 下{d_down:.0f} 左{d_left:.0f} 右{d_right:.0f}")

# --- 画在图上验证 ---
img = Image.open(f'{out_dir}/1F_page4.png')
pw, ph = page.rect.width, page.rect.height
sx, sy = img.width / pw, img.height / ph

draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

colors_list = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FF8800']
for i, (name, bbox) in enumerate(room_boundaries.items()):
    x0, y0, x1, y1 = bbox
    ix0, iy0 = int(x0*sx), int(y0*sy)
    ix1, iy1 = int(x1*sx), int(y1*sy)
    color = colors_list[i % len(colors_list)]
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=2)
    draw.text((ix0+3, iy0+3), name, fill=color, font=font)

out = f'{out_dir}/1F_step2_boundaries.png'
img.save(out)
print(f"\n工序2输出: {out}")
doc.close()
