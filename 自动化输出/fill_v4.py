# -*- coding: utf-8 -*-
"""
1F示意图 — 最近墙体法
从标签位置向四个方向找最近的墙体填充线/粗线条
"""
import fitz
import numpy as np
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

# 收集墙体线段（填充线+粗线条）
h_walls = []  # (y, x0, x1) 水平墙
v_walls = []  # (x, y0, y1) 垂直墙

for p in page.get_drawings():
    fill = p.get('fill')
    width = p.get('width', 0)
    is_wall_fill = (fill == (0.0, 0.0, 0.0) and width == 0)
    is_thick = (width >= 0.72)
    if not is_wall_fill and not is_thick:
        continue
    
    for item in p['items']:
        if item[0] == 'l':
            x0,y0,x1,y1 = item[1].x, item[1].y, item[2].x, item[2].y
            L = ((x1-x0)**2+(y1-y0)**2)**0.5
            if L < 10:
                continue
            # 近似水平
            if abs(y1-y0) < 3:
                h_walls.append((y0, min(x0,x1), max(x0,x1)))
            # 近似垂直
            elif abs(x1-x0) < 3:
                v_walls.append((x0, min(y0,y1), max(y0,y1)))

print(f"水平墙: {len(h_walls)}, 垂直墙: {len(v_walls)}")

# 从标签位置找最近的墙
def find_nearest_h_wall(cx, cy, direction):
    """找最近的水平墙（上下方向）
    direction: 'up'=找上方的墙, 'down'=找下方的墙
    """
    best = None
    best_dist = 9999
    for wy, wx0, wx1 in h_walls:
        # 墙要在cx的范围内（或接近）
        if wx0 - 30 <= cx <= wx1 + 30:
            if direction == 'up' and wy < cy:
                d = cy - wy
                if d < best_dist and d > 5:
                    best_dist = d
                    best = wy
            elif direction == 'down' and wy > cy:
                d = wy - cy
                if d < best_dist and d > 5:
                    best_dist = d
                    best = wy
    return best, best_dist

def find_nearest_v_wall(cx, cy, direction):
    """找最近的垂直墙（左右方向）"""
    best = None
    best_dist = 9999
    for wx, wy0, wy1 in v_walls:
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

# 为每个标签找边界
print("\n=== 每个房间的边界 ===")
rooms = {}
for name, cx, cy in labels:
    up, d_up = find_nearest_h_wall(cx, cy, 'up')
    down, d_down = find_nearest_h_wall(cx, cy, 'down')
    left, d_left = find_nearest_v_wall(cx, cy, 'left')
    right, d_right = find_nearest_v_wall(cx, cy, 'right')
    
    # 兜底：找不到墙用默认值
    if up is None: up = cy - 100
    if down is None: down = cy + 100
    if left is None: left = cx - 100
    if right is None: right = cx + 100
    
    margin = 5
    x0 = min(left, right) + margin
    y0 = min(up, down) + margin
    x1 = max(left, right) - margin
    y1 = max(up, down) - margin
    
    rooms[name] = (x0, y0, x1, y1)
    w, h = x1-x0, y1-y0
    print(f"  {name}: ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) {w:.0f}x{h:.0f}  距离: 上{d_up:.0f} 下{d_down:.0f} 左{d_left:.0f} 右{d_right:.0f}")

# 解决重叠：小房间优先
def area(bbox):
    return max(0,bbox[2]-bbox[0]) * max(0,bbox[3]-bbox[1])

# 按面积从小到大排序
sorted_rooms = sorted(rooms.items(), key=lambda x: area(x[1]))

# 去重：已经被分配的区域不能再被占用
# 用网格级别的去重
GRID = 2
gw, gh = int(pw/GRID)+1, int(ph/GRID)+1
assigned = np.zeros((gh, gw), dtype=bool)

final_rooms = {}
for name, (x0, y0, x1, y1) in sorted_rooms:
    # 转网格坐标
    gx0 = max(0, int(x0/GRID))
    gy0 = max(0, int(y0/GRID))
    gx1 = min(gw-1, int(x1/GRID))
    gy1 = min(gh-1, int(y1/GRID))
    
    # 取未被分配的区域
    mask = np.zeros((gh, gw), dtype=bool)
    mask[gy0:gy1+1, gx0:gx1+1] = True
    mask &= ~assigned
    
    if mask.sum() > 0:
        assigned |= mask
        ys, xs = np.where(mask)
        final_rooms[name] = (xs.min()*GRID, ys.min()*GRID, (xs.max()+1)*GRID, (ys.max()+1)*GRID)

print(f"\n=== 最终 {len(final_rooms)} 个房间 ===")
for name, (x0,y0,x1,y1) in final_rooms.items():
    print(f"  {name}: ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f}) {x1-x0:.0f}x{y1-y0:.0f}")

# 画图
sx, sy = iw/pw, ih/ph
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
    
    # 半透明填充
    overlay = Image.new('RGBA', canvas.size, (0,0,0,0))
    ImageDraw.Draw(overlay).rectangle([ix0,iy0,ix1,iy1], fill=color)
    canvas = Image.alpha_composite(canvas, overlay)
    
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([ix0,iy0,ix1,iy1], outline=color[:3]+(200,), width=2)
    draw.text((ix0+5, iy0+5), name, fill=(0,0,0,255), font=font)

canvas.convert('RGB').save(f'{out_dir}/step1_final.png', quality=95)
print(f"\n✅ step1_final.png")
doc.close()
