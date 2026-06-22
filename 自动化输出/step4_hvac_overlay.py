"""
工序4：在已识别的房间边界上叠加暖通方案
1F首层 → 空调示意图 + 地暖示意图
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
from collections import deque

pdf_path = r'C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf'
out_dir = r'C:\Users\apple\Desktop\湖滨壹号_自动化输出'

doc = fitz.open(pdf_path)
page = doc[3]  # 1F
pw, ph = page.rect.width, page.rect.height

# --- 提取标签和墙体 ---
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

# --- 找边界（沿用step3v5的方法）---
def find_all_walls(walls, direction, cx, cy, is_h=True, max_dist=200):
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

def pick_wall(wall_list, prefer='far'):
    if not wall_list:
        return None
    if prefer == 'far':
        for d, w in reversed(wall_list):
            if d > 40:
                return w
        return wall_list[-1][1]
    else:
        return wall_list[0][1]

room_boundaries = {}
for name, cx, cy in unique_labels:
    up_walls = find_all_walls(h_walls, 'up', cx, cy, True)
    down_walls = find_all_walls(h_walls, 'down', cx, cy, True)
    left_walls = find_all_walls(v_walls, 'left', cx, cy, False)
    right_walls = find_all_walls(v_walls, 'right', cx, cy, False)
    
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

# --- 暖通方案规则表 ---
# 空调方案
ac_zones = {
    '休闲区':   {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '风管机 8.5kW × 2', 'note': '客厅/休闲区'},
    '餐厅':     {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '风管机 5.6kW', 'note': '餐厅区'},
    '厨房':     {'zone': '厨房专用区', 'color': (255, 220, 150), 'equipment': '厨房空调 3.5kW', 'note': '防油烟设计'},
    '卧室A':    {'zone': '私密休息区', 'color': (200, 180, 255), 'equipment': '风管机 3.5kW', 'note': '主卧'},
    '卧室B':    {'zone': '私密休息区', 'color': (200, 180, 255), 'equipment': '风管机 3.5kW', 'note': '次卧'},
    '卧室C':    {'zone': '私密休息区', 'color': (200, 180, 255), 'equipment': '风管机 3.5kW', 'note': '书房'},
    '卫生间':   {'zone': '卫浴区',     'color': (180, 255, 180), 'equipment': '卫浴空调 1.5kW', 'note': '防潮设计'},
    '庭院花园': {'zone': '过渡区',     'color': (220, 220, 220), 'equipment': '无/自然通风', 'note': '室外区域'},
    '楼梯厅':   {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '无', 'note': '自然通风'},
    '酒柜':     {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '无', 'note': '小型储藏'},
    '影音室':   {'zone': '娱乐区',     'color': (255, 200, 255), 'equipment': '风管机 5.6kW', 'note': '隔音处理'},
    '品茶区':   {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '风管机 5.6kW', 'note': '休闲区'},
    '娱乐区':   {'zone': '娱乐区',     'color': (255, 200, 255), 'equipment': '风管机 5.6kW', 'note': '多功能区'},
    '书房':     {'zone': '私密休息区', 'color': (200, 180, 255), 'equipment': '风管机 3.5kW', 'note': '书房'},
    '车库':     {'zone': '车库区',     'color': (200, 200, 200), 'equipment': '无', 'note': '自然通风'},
    '鞋帽间':   {'zone': '公共核心区', 'color': (255, 180, 180), 'equipment': '无', 'note': '小型储藏'},
    '衣帽间':   {'zone': '私密休息区', 'color': (200, 180, 255), 'equipment': '无', 'note': '主卧附属'},
}

# 地暖方案
heat_zones = {
    '休闲区':   {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '餐厅':     {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '厨房':     {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '卫生间':   {'zone': '电地暖-卫浴',   'color': (180, 255, 200), 'pipe': '发热电缆', 'spacing': '100mm', 'temp': '供水35℃'},
    '庭院花园': {'zone': '无地暖',       'color': (230, 230, 230), 'pipe': '无', 'spacing': '无', 'temp': '室外'},
    '楼梯厅':   {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '酒柜':     {'zone': '无地暖',       'color': (230, 230, 230), 'pipe': '无', 'spacing': '无', 'temp': '小型空间'},
    '影音室':   {'zone': '水地暖-休息区', 'color': (200, 180, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '150mm', 'temp': '供水40℃'},
    '品茶区':   {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '娱乐区':   {'zone': '水地暖-公共区', 'color': (180, 200, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '200mm', 'temp': '供水45℃'},
    '书房':     {'zone': '水地暖-休息区', 'color': (200, 180, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '150mm', 'temp': '供水40℃'},
    '车库':     {'zone': '无地暖',       'color': (230, 230, 230), 'pipe': '无', 'spacing': '无', 'temp': '车库'},
    '卧室A':    {'zone': '水地暖-休息区', 'color': (200, 180, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '150mm', 'temp': '供水40℃'},
    '卧室B':    {'zone': '水地暖-休息区', 'color': (200, 180, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '150mm', 'temp': '供水40℃'},
    '卧室C':    {'zone': '水地暖-休息区', 'color': (200, 180, 255), 'pipe': 'PE-RT管 D20×2.0', 'spacing': '150mm', 'temp': '供水40℃'},
}

# --- 绘制函数 ---
def draw_overlay(base_img, room_bboxes, zone_config, title, info_key='equipment'):
    img = base_img.copy()
    draw = ImageDraw.Draw(img, 'RGBA')
    
    try:
        font = ImageFont.truetype("arial.ttf", 14)
        font_sm = ImageFont.truetype("arial.ttf", 11)
        font_title = ImageFont.truetype("arial.ttf", 22)
    except:
        font = ImageFont.load_default()
        font_sm = font
        font_title = font
    
    sx = img.width / pw
    sy = img.height / ph
    
    # 半透明叠加
    for name, bbox in room_bboxes.items():
        # 匹配暖通规则（模糊匹配）
        matched = None
        for zone_name in zone_config:
            if zone_name in name or name in zone_name:
                matched = zone_config[zone_name]
                break
        
        if matched is None:
            # 默认：未匹配的房间用灰色
            matched = {'zone': '未配置', 'color': (200, 200, 200), info_key: '待配置'}
        
        x0, y0, x1, y1 = bbox
        ix0, iy0 = int(x0*sx), int(y0*sy)
        ix1, iy1 = int(x1*sx), int(y1*sy)
        
        color = matched['color']
        # 半透明填充
        draw.rectangle([ix0, iy0, ix1, iy1], fill=color + (100,), outline=color + (200,), width=2)
        
        # 房间名 + 设备信息
        info = matched.get(info_key, '')
        draw.text((ix0+5, iy0+5), name, fill=(0, 0, 0), font=font)
        if info:
            draw.text((ix0+5, iy0+22), info, fill=(60, 60, 60), font=font_sm)
    
    # 标题
    draw.text((20, 15), title, fill=(0, 0, 0), font=font_title)
    
    return img

# --- 生成空调示意图 ---
img_orig = Image.open(f'{out_dir}/1F_page4.png')
img_ac = draw_overlay(img_orig, room_boundaries, ac_zones,
                      '1F 首层 — 空调及新风示意图', 'equipment')
img_ac.save(f'{out_dir}/1F_AC_final.png')
print(f"空调示意图: {out_dir}/1F_AC_final.png")

# --- 生成地暖示意图 ---
img_heat = draw_overlay(img_orig, room_boundaries, heat_zones,
                        '1F 首层 — 地暖示意图', 'pipe')
img_heat.save(f'{out_dir}/1F_HEAT_final.png')
print(f"地暖示意图: {out_dir}/1F_HEAT_final.png")

# --- 生成图例 ---
legend_w, legend_h = 400, 300
legend_ac = Image.new('RGBA', (legend_w, legend_h), (255, 255, 255, 255))
ld = ImageDraw.Draw(legend_ac)
try:
    font = ImageFont.truetype("arial.ttf", 14)
except:
    font = ImageFont.load_default()

ld.text((10, 10), '空调分区图例', fill=(0, 0, 0), font=font)
zones_seen = set()
y = 40
for name in room_boundaries:
    for zone_name, cfg in ac_zones.items():
        if zone_name in name and cfg['zone'] not in zones_seen:
            zones_seen.add(cfg['zone'])
            ld.rectangle([10, y, 40, y+20], fill=cfg['color'] + (200,))
            ld.text((50, y), f"{cfg['zone']} - {cfg['equipment']}", fill=(0, 0, 0), font=font)
            y += 30
legend_ac.save(f'{out_dir}/1F_AC_legend.png')

doc.close()
print("\n工序4完成！")
