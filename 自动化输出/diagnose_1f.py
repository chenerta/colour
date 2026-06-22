# -*- coding: utf-8 -*-
"""
诊断脚本：只做一件事 — 在原图上标出文字标签位置和墙体网格
先确认基础数据对不对，再谈方案
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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

# ===== 渲染原图 =====
mat = fitz.Matrix(2, 2)
pix = page.get_pixmap(matrix=mat)
img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
sx, sy = img.width / pw, img.height / ph
print(f"PDF: {pw:.0f}x{ph:.0f}, Image: {img.width}x{img.height}, Scale: {sx:.2f}x{sy:.2f}")

# ===== 提取所有中文文字 =====
blocks = page.get_text('dict')['blocks']
room_kw = ['厨房','卫生间','餐厅','庭院','花园','休闲','楼梯','酒柜',
           '客厅','卧室','书房','影音','品茶','娱乐','车库','鞋帽','衣帽','储藏','设备']
seen = set()
labels = []
all_texts = []
for b in blocks:
    if 'lines' not in b: continue
    for line in b['lines']:
        for span in line['spans']:
            t = span['text'].strip()
            if not t: continue
            x0, y0, x1, y1 = span['bbox']
            cx, cy = (x0+x1)/2, (y0+y1)/2
            all_texts.append((t, cx, cy))
            for kw in room_kw:
                if kw in t and 'TITLE' not in t and 'PROJECT' not in t:
                    key = t[:2]
                    if key not in seen:
                        seen.add(key)
                        labels.append((t, cx, cy))
                    break

print(f"\n=== 找到 {len(labels)} 个房间标签 ===")
for name, cx, cy in labels:
    ix, iy = int(cx*sx), int(cy*sy)
    print(f"  '{name}': PDF({cx:.1f},{cy:.1f}) -> Image({ix},{iy})")

# ===== 提取墙体线段 =====
h_lines = []
v_lines = []
for p in page.get_drawings():
    for item in p["items"]:
        if item[0] == "l":
            x0,y0 = item[1].x, item[1].y
            x1,y1 = item[2].x, item[2].y
            L = ((x1-x0)**2+(y1-y0)**2)**0.5
            if L > 80:
                if abs(y1-y0) < 2:
                    h_lines.append((min(x0,x1), y0, max(x0,x1), y1))
                elif abs(x1-x0) < 2:
                    v_lines.append((x0, min(y0,y1), x1, max(y0,y1)))

print(f"\n=== 墙体线条: {len(h_lines)} 水平, {len(v_lines)} 垂直 ===")

# ===== 诊断图1：标出文字标签位置 =====
img1 = img.copy()
draw1 = ImageDraw.Draw(img1)
font = get_font(16)
font_sm = get_font(12)

for name, cx, cy in labels:
    ix, iy = int(cx*sx), int(cy*sy)
    # 画红色圆点
    r = 6
    draw1.ellipse([ix-r, iy-r, ix+r, iy+r], fill='red', outline='white', width=2)
    # 画标签名
    draw1.text((ix+10, iy-8), name, fill='red', font=font)

img1.save(f'{out_dir}/diag1_labels.png', quality=95)
print(f"\n✅ 诊断图1: diag1_labels.png (标签位置)")

# ===== 诊断图2：标出墙体线段 =====
img2 = img.copy()
draw2 = ImageDraw.Draw(img2)

# 画水平墙
for x0,y0,x1,y1 in h_lines:
    draw2.line([(int(x0*sx), int(y0*sy)), (int(x1*sx), int(y1*sy))], fill='blue', width=2)

# 画垂直墙
for x0,y0,x1,y1 in v_lines:
    draw2.line([(int(x0*sx), int(y0*sy)), (int(x1*sx), int(y1*sy))], fill='green', width=2)

# 同时标出标签
for name, cx, cy in labels:
    ix, iy = int(cx*sx), int(cy*sy)
    r = 5
    draw2.ellipse([ix-r, iy-r, ix+r, iy+r], fill='red', outline='white', width=2)
    draw2.text((ix+10, iy-8), name, fill='red', font=font)

img2.save(f'{out_dir}/diag2_walls.png', quality=95)
print(f"✅ 诊断图2: diag2_walls.png (墙体+标签)")

# ===== 诊断图3：网格化墙体 + 泛洪起点 =====
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

# 把网格渲染成图片（白=空，黑=墙，红点=标签位置）
grid_img = Image.new('RGB', (gw, gh), (255, 255, 255))
pixels = grid_img.load()
for y in range(gh):
    for x in range(gw):
        if wall[y][x]:
            pixels[x, y] = (0, 0, 0)

# 标签位置
for name, cx, cy in labels:
    gx, gy = int(cx/GRID), int(cy/GRID)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            ny, nx = gy+dy, gx+dx
            if 0<=ny<gh and 0<=nx<gw:
                pixels[nx, ny] = (255, 0, 0)

# 放大显示
scale = 4
grid_big = grid_img.resize((gw*scale, gh*scale), Image.NEAREST)
grid_big.save(f'{out_dir}/diag3_grid.png', quality=95)
print(f"✅ 诊断图3: diag3_grid.png (网格视图: 黑=墙, 红=标签)")

doc.close()
print("\n=== 请查看3张诊断图，确认：===")
print("1. diag1: 红点是否在对应房间的中心？")
print("2. diag2: 蓝/绿线是否和墙体对齐？")
print("3. diag3: 网格上红色标记是否在空白区域（非黑色墙体）？")
