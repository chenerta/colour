# -*- coding: utf-8 -*-
"""
1F首层暖通示意图 — 最终版
解决：1)中文字体 2)开放空间划分 3)边界精度
"""
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir  = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

# ===== 中文字体 =====
def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        try:
            return ImageFont.truetype(fp, size)
        except:
            continue
    return ImageFont.load_default()

# ===== 读取PDF =====
doc = fitz.open(pdf_path)
page = doc[3]  # 第4页 = 1F
pw, ph = page.rect.width, page.rect.height
print(f"PDF: {pw:.0f}x{ph:.0f}")

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

# ===== 泛洪+Voronoi混合 =====
# 每个标签向外泛洪（不穿越墙体），记录覆盖的网格
room_cells = {}
for name, cx, cy in labels:
    gx, gy = int(cx/GRID), int(cy/GRID)
    # 如果标签在墙上，找最近空位
    if wall[gy][gx]:
        for r in range(1,50):
            found = False
            for ddx in range(-r,r+1):
                for ddy in range(-r,r+1):
                    nx,ny = gx+ddx, gy+ddy
                    if 0<=nx<gw and 0<=ny<gh and not wall[ny][nx]:
                        gx,gy = nx,ny; found = True; break
                if found: break
            if found: break
    
    # 泛洪
    visited = set()
    q = deque([(gx,gy,0)])
    visited.add((gx,gy))
    while q:
        x,y,d = q.popleft()
        if d >= 80:  # 最大80格=160pt
            continue
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx,ny = x+dx, y+dy
            if 0<=nx<gw and 0<=ny<gh and (nx,ny) not in visited and not wall[ny][nx]:
                visited.add((nx,ny))
                q.append((nx,ny,d+1))
    room_cells[name] = visited
    print(f"  {name}: 起点({gx},{gy}), 覆盖{len(visited)}网格")

# ===== 去重：小房间优先 =====
# 按面积从小到大排序
sorted_rooms = sorted(room_cells.items(), key=lambda x: len(x[1]))
assigned = set()
room_final = {}

for name, cells in sorted_rooms:
    my_cells = cells - assigned
    assigned |= my_cells
    if my_cells:
        xs = [c[0] for c in my_cells]
        ys = [c[1] for c in my_cells]
        room_final[name] = (min(xs)*GRID, min(ys)*GRID, (max(xs)+1)*GRID, (max(ys)+1)*GRID)

print("\n=== 最终边界 ===")
for name, (x0,y0,x1,y1) in room_final.items():
    print(f"  {name}: ({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) {(x1-x0):.0f}x{(y1-y0):.0f}")

# ===== 暖通方案 =====
# 空调分区
ac_config = {
    '休闲区':   {'zone':'公共核心区', 'c':(255,180,180), 'eq':'风管机 8.5kW×2'},
    '餐厅':     {'zone':'公共核心区', 'c':(255,180,180), 'eq':'风管机 5.6kW'},
    '楼梯厅':   {'zone':'公共核心区', 'c':(255,200,200), 'eq':'自然通风'},
    '酒柜':     {'zone':'公共核心区', 'c':(255,200,200), 'eq':'—'},
    '厨房':     {'zone':'厨房专用区', 'c':(255,220,150), 'eq':'厨房空调 3.5kW'},
    '卫生间':   {'zone':'卫浴区',    'c':(180,255,180), 'eq':'卫浴空调 1.5kW'},
    '庭院花园': {'zone':'室外区域',  'c':(230,230,230), 'eq':'自然通风'},
}

# 地暖分区
heat_config = {
    '休闲区':   {'zone':'水地暖-公共区','c':(180,200,255), 'eq':'PE-RT D20 间距200mm'},
    '餐厅':     {'zone':'水地暖-公共区','c':(180,200,255), 'eq':'PE-RT D20 间距200mm'},
    '楼梯厅':   {'zone':'水地暖-公共区','c':(200,215,255), 'eq':'PE-RT D20 间距200mm'},
    '酒柜':     {'zone':'不铺设',      'c':(230,230,230), 'eq':'不铺设'},
    '厨房':     {'zone':'水地暖-公共区','c':(180,200,255), 'eq':'PE-RT D20 间距200mm'},
    '卫生间':   {'zone':'电地暖-卫浴', 'c':(180,255,200), 'eq':'发热电缆 间距100mm'},
    '庭院花园': {'zone':'不铺设',      'c':(230,230,230), 'eq':'不铺设'},
}

# ===== 绘图 =====
def draw_hvac(base_img, room_bboxes, config, title, info_key='eq'):
    img = base_img.convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    
    sx = img.width / pw
    sy = img.height / ph
    
    for name, (x0,y0,x1,y1) in room_bboxes.items():
        # 匹配规则
        cfg = None
        for k,v in config.items():
            if k in name:
                cfg = v; break
        if cfg is None:
            cfg = {'zone':'未配置','c':(200,200,200),'eq':'待配置'}
        
        ix0,iy0 = int(x0*sx), int(y0*sy)
        ix1,iy1 = int(x1*sx), int(y1*sy)
        
        # 半透明填充
        od.rectangle([ix0,iy0,ix1,iy1], fill=cfg['c']+(120,))
    
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)
    
    # 边框 + 文字
    font = get_font(14)
    font_sm = get_font(11)
    font_title = get_font(22)
    font_legend = get_font(12)
    
    for name, (x0,y0,x1,y1) in room_bboxes.items():
        cfg = None
        for k,v in config.items():
            if k in name:
                cfg = v; break
        if cfg is None:
            cfg = {'zone':'未配置','c':(200,200,200),'eq':'待配置'}
        
        ix0,iy0 = int(x0*sx), int(y0*sy)
        ix1,iy1 = int(x1*sx), int(y1*sy)
        
        # 边框
        draw.rectangle([ix0,iy0,ix1,iy1], outline=cfg['c'][:3]+(200,), width=2)
        
        # 房间名（白底黑字）
        bbox_t = font.getbbox(name)
        tw,th = bbox_t[2]-bbox_t[0], bbox_t[3]-bbox_t[1]
        draw.rectangle([ix0+3,iy0+3, ix0+tw+9, iy0+th+9], fill=(255,255,255,220))
        draw.text((ix0+6, iy0+5), name, fill=(0,0,0), font=font)
        
        # 设备标注
        eq = cfg.get(info_key,'')
        if eq and eq != '—':
            bbox_e = font_sm.getbbox(eq)
            ew,eh = bbox_e[2]-bbox_e[0], bbox_e[3]-bbox_e[1]
            draw.rectangle([ix0+3,iy0+th+12, ix0+ew+9, iy0+th+eh+16], fill=cfg['c'][:3]+(200,))
            draw.text((ix0+6, iy0+th+13), eq, fill=(0,0,0), font=font_sm)
    
    # 标题栏
    draw.rectangle([10,10, 500,45], fill=(40,40,40,230))
    draw.text((15,14), title, fill=(255,255,255), font=font_title)
    
    # 图例
    zones_done = set()
    lx, ly = img.width - 350, 10
    legend_items = []
    for name in room_bboxes:
        for k,v in config.items():
            if k in name and v['zone'] not in zones_done:
                zones_done.add(v['zone'])
                legend_items.append((v['zone'], v['c'], v.get(info_key,'')))
    
    lh = len(legend_items) * 28 + 36
    draw.rectangle([lx,ly, img.width-10, ly+lh], fill=(255,255,255,230))
    draw.rectangle([lx,ly, img.width-10, ly+lh], outline=(100,100,100), width=1)
    draw.text((lx+8, ly+6), '图例', fill=(0,0,0), font=font)
    for i,(zone_name, color, eq) in enumerate(legend_items):
        yy = ly + 30 + i*28
        draw.rectangle([lx+8,yy,lx+28,yy+18], fill=color+(200,))
        draw.rectangle([lx+8,yy,lx+28,yy+18], outline=(0,0,0), width=1)
        label = f"{zone_name}"
        if eq:
            label += f" ({eq})"
        draw.text((lx+32, yy+1), label, fill=(0,0,0), font=font_legend)
    
    return img.convert('RGB')

# ===== 生成 =====
base = Image.open(f'{out_dir}/1F_page4.png')

img_ac = draw_hvac(base, room_final, ac_config, '1F首层 — 空调及新风示意图')
img_ac.save(f'{out_dir}/1F_AC_v2.png', quality=95)
print(f"\n✅ 空调图: 1F_AC_v2.png")

img_heat = draw_hvac(base, room_final, heat_config, '1F首层 — 地暖示意图', 'eq')
img_heat.save(f'{out_dir}/1F_HEAT_v2.png', quality=95)
print(f"✅ 地暖图: 1F_HEAT_v2.png")

doc.close()
