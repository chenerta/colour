"""
工序3：解决房间重叠问题
策略：
1. 对每个房间，找所有方向的候选墙（不限距离）
2. 用最近的墙作为边界
3. 如果两个房间重叠，把重叠区域分给更小的那个房间
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
                    h_walls.append((min(x0,x1), y0, max(x0,x1)))
                elif abs(x0 - x1) < 3:
                    v_walls.append((x0, min(y0,y1), max(y0,y1)))

print(f"水平墙线: {len(h_walls)}, 垂直墙线: {len(v_walls)}")

# --- 找最近墙（无最小距离限制）---
def find_nearest_wall(walls, direction, cx, cy, is_horizontal=True):
    best = None
    best_dist = 9999
    
    if is_horizontal:
        for wx0, wy, wx1 in walls:
            if wx0 - 30 <= cx <= wx1 + 30:
                if direction == 'up' and wy < cy:
                    d = cy - wy
                    if d < best_dist and d > 5:  # 至少5pt避免标签自身
                        best_dist = d
                        best = wy
                elif direction == 'down' and wy > cy:
                    d = wy - cy
                    if d < best_dist and d > 5:
                        best_dist = d
                        best = wy
    else:
        for wx, wy0, wy1 in walls:
            if wy0 - 30 <= cy <= wy1 + 30:
                if direction == 'left' and wx < cx:
                    d = cx - wx
                    if d < best_dist and d > 5:
                        best_dist = d
                        best = wx
                elif direction == 'right' and wx > cx:
                    d = wx - cx
                    if d < best_dist and d > 5:
                        best_dist = d
                        best = wx
    return best, best_dist

# --- 第一轮：计算所有房间的初始边界 ---
room_bboxes = {}
for name, cx, cy in unique_labels:
    up, _ = find_nearest_wall(h_walls, 'up', cx, cy, True)
    down, _ = find_nearest_wall(h_walls, 'down', cx, cy, True)
    left, _ = find_nearest_wall(v_walls, 'left', cx, cy, False)
    right, _ = find_nearest_wall(v_walls, 'right', cx, cy, False)
    
    if up is None: up = cy - 100
    if down is None: down = cy + 100
    if left is None: left = cx - 100
    if right is None: right = cx + 100
    
    margin = 5
    x0, y0 = min(left, right) + margin, min(up, down) + margin
    x1, y1 = max(left, right) - margin, max(up, down) - margin
    room_bboxes[name] = [x0, y0, x1, y1]

# --- 第二轮：解决重叠 ---
def area(bbox):
    return max(0, bbox[2]-bbox[0]) * max(0, bbox[3]-bbox[1])

def overlap(a, b):
    """返回重叠区域，没有重叠返回None"""
    ox0 = max(a[0], b[0])
    oy0 = max(a[1], b[1])
    ox1 = min(a[2], b[2])
    oy1 = min(a[3], b[3])
    if ox0 < ox1 and oy0 < oy1:
        return [ox0, oy0, ox1, oy1]
    return None

# 迭代解决重叠：重叠区域归面积更小的房间
for _ in range(10):
    names = list(room_bboxes.keys())
    fixed = False
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a_name, b_name = names[i], names[j]
            a, b = room_bboxes[a_name], room_bboxes[b_name]
            ol = overlap(a, b)
            if ol is None:
                continue
            
            # 重叠区域归更小的房间（更具体的房间优先）
            a_area = area(a)
            b_area = area(b)
            
            if a_area <= b_area:
                # a更小，保留a，裁剪b
                # 裁剪方向：选择重叠最窄的方向
                dx_left = ol[2] - a[0]  # a的左边到重叠右边
                dx_right = a[2] - ol[0]  # a的右边到重叠左边
                dy_top = ol[3] - a[1]
                dy_bottom = a[3] - ol[1]
                
                min_cut = min(dx_left, dx_right, dy_top, dy_bottom)
                if min_cut == dx_left:
                    b[0] = ol[2]  # b的左边移到重叠右边
                elif min_cut == dx_right:
                    b[2] = ol[0]
                elif min_cut == dy_top:
                    b[1] = ol[3]
                else:
                    b[3] = ol[1]
                fixed = True
            else:
                # b更小，保留b，裁剪a
                dx_left = ol[2] - b[0]
                dx_right = b[2] - ol[0]
                dy_top = ol[3] - b[1]
                dy_bottom = b[3] - ol[1]
                
                min_cut = min(dx_left, dx_right, dy_top, dy_bottom)
                if min_cut == dx_left:
                    a[0] = ol[2]
                elif min_cut == dx_right:
                    a[2] = ol[0]
                elif min_cut == dy_top:
                    a[1] = ol[3]
                else:
                    a[3] = ol[1]
                fixed = True
    if not fixed:
        break

# --- 输出结果 ---
print("\n=== 最终房间边界 ===")
for name, bbox in room_bboxes.items():
    x0, y0, x1, y1 = bbox
    w, h = x1-x0, y1-y0
    print(f"  {name}: ({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) 尺寸={w:.0f}x{h:.0f}")

# 检查是否还有重叠
print("\n=== 重叠检查 ===")
names = list(room_bboxes.keys())
has_overlap = False
for i in range(len(names)):
    for j in range(i+1, len(names)):
        ol = overlap(room_bboxes[names[i]], room_bboxes[names[j]])
        if ol:
            print(f"  ⚠ {names[i]} 和 {names[j]} 重叠: ({ol[0]:.0f},{ol[1]:.0f},{ol[2]:.0f},{ol[3]:.0f})")
            has_overlap = True
if not has_overlap:
    print("  ✓ 无重叠")

# --- 画图 ---
img = Image.open(f'{out_dir}/1F_page4.png')
pw, ph = page.rect.width, page.rect.height
sx, sy = img.width / pw, img.height / ph

draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

colors_list = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#FF8800']
for i, (name, bbox) in enumerate(room_bboxes.items()):
    x0, y0, x1, y1 = bbox
    ix0, iy0 = int(x0*sx), int(y0*sy)
    ix1, iy1 = int(x1*sx), int(y1*sy)
    color = colors_list[i % len(colors_list)]
    draw.rectangle([ix0, iy0, ix1, iy1], outline=color, width=3)
    draw.text((ix0+3, iy0+3), name, fill=color, font=font)

out = f'{out_dir}/1F_step3_no_overlap.png'
img.save(out)
print(f"\n工序3输出: {out}")
doc.close()
