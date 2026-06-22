"""
工序2v2：改进的房间边界识别
改进点：跳过过近的内部隔墙，设定最小房间尺寸
"""
import fitz
from PIL import Image, ImageDraw, ImageFont

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F

# --- 提取房间标签 ---
blocks = page.get_text('dict')['blocks'
]
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

# --- 提取墙体线条 ---
paths = page.get_drawings()
h_walls = []
v_walls = []

for p in paths:
    for item in p["items"]:
        if item[0] == "l":
            x0, y0 = item[1].x, item[1].y
            x1, y1 = item[2].x, item[2].y
            length = ((x1-x0)**2 + (y1-y0)**2) ** 0.5
            if length > 15:
                if abs(y0 - y1) < 3:
                    h_walls.append((min(x0,x1), y0, max(x0,x1), y0))
                elif abs(x0 - x1) < 3:
                    v_walls.append((x0, min(y0,y1), x0, max(y0,y1)))

# --- 改进的边界查找 ---
def find_boundary(walls, direction, cx, cy, is_horizontal=True, min_dist=80):
    """找房间边界：跳过太近的墙（内部隔墙），找合理距离的墙"""
    candidates = []
    
    if is_horizontal:
        for wx0, wy, wx1, wy1 in walls:
            if wx0 - 20 <= cx <= wx1 + 20:
                if direction == 'up' and wy < cy:
                    dist = cy - wy
                    if dist > min_dist:
                        candidates.append((dist, wy))
                elif direction == 'down' and wy > cy:
                    dist = wy - cy
                    if dist > min_dist:
                        candidates.append((dist, wy))
    else:
        for wx, wy0, wx1, wy1 in walls:
            if wy0 - 20 <= cy <= wy1 + 20:
                if direction == 'left' and wx < cx:
                    dist = cx - wx
                    if dist > min_dist:
                        candidates.append((dist, wx))
                elif direction == 'right' and wx > cx:
                    dist = wx - cx
                    if dist > min_dist:
                        candidates.append((dist, wx))
    
    if candidates:
        candidates.sort()
        # 取最近的满足min_dist的墙
        return candidates[0][1], candidates[0][0]
    return None, 0

# 计算边界
print("=== 房间边界（改进版）===")
room_boundaries = {}
for name, cx, cy in unique_labels:
    # 不同类型房间用不同的最小尺寸
    min_d = 60
    if '厨房' in name or '餐厅' in name:
        min_d = 80
    elif '庭院' in name or '花园' in name or '休闲' in name:
        min_d = 100
    elif '楼梯' in name:
        min_d = 50
    elif '酒柜' in name:
        min_d = 20
    
    wall_up, d_up = find_boundary(h_walls, 'up', cx, cy, True, min_d)
    wall_down, d_down = find_boundary(h_walls, 'down', cx, cy, True, min_d)
    wall_left, d_left = find_boundary(v_walls, 'left', cx, cy, False, min_d)
    wall_right, d_right = find_boundary(v_walls, 'right', cx, cy, False, min_d)
    
    # 兜底：找不到墙就用固定范围
    if wall_up is None: wall_up = cy - 150
    if wall_down is None: wall_down = cy + 150
    if wall_left is None: wall_left = cx - 150
    if wall_right is None: wall_right = cx + 150
    
    # 确保边界合理
    margin = 10
    x0 = min(wall_left, wall_right) + margin
    y0 = min(wall_up, wall_down) + margin
    x1 = max(wall_left, wall_right) - margin
    y1 = max(wall_up, wall_down) - margin
    
    # 确保y1 > y0
    if y1 <= y0:
        y1 = y0 + 50
    
    bbox = (x0, y0, x1, y1)
    room_boundaries[name] = bbox
    w = x1 - x0
    h = y1 - y0
    print(f"  {name}: PDF({cx:.0f},{cy:.0f}) 边界=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) 尺寸={w:.0f}x{h:.0f}")

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
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
    draw.text((ix0+3, iy0+3), name, fill=color, font=font)

out = f'{out_dir}/1F_step2v2_boundaries.png'
img.save(out)
print(f"\n工序2输出: {out}")
doc.close()
