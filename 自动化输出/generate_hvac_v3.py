# -*- coding: utf-8 -*-
"""
基于精确坐标生成空调和地暖示意图 - 修复版
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 加载原图
img_path = '试验原图.png'
original = Image.open(img_path).convert('RGBA')
w, h = original.size
print(f"原图尺寸: {w}x{h}")

# ============================================================
# 精确房间坐标（视觉模型从原图中提取）
# ============================================================
rooms = {
    '入户门厅':    (174, 176, 450, 286),
    '设备间':      (669, 183, 714, 388),
    '楼梯间':      (500, 181, 667, 386),
    '客厅':        (172, 376, 674, 671),
    '餐厅':        (502, 398, 701, 590),
    '公共卫生间':  (722, 201, 850, 313),
    '衣帽间':      (718, 316, 848, 428),
    '厨房':        (718, 355, 849, 666),
    '客卧':        (717, 674, 850, 941),
    '户外露台':    (171, 670, 714, 861),
}

# ============================================================
# 空调分区方案
# ============================================================
ac_zones = [
    {
        'name': '公共核心区',
        'rooms': ['客厅', '餐厅'],
        'color': (66, 133, 244, 90),
        'equipment': '风管机/中央空调',
        'load': '8.5kW',
    },
    {
        'name': '过渡辅助区',
        'rooms': ['入户门厅'],
        'color': (156, 39, 176, 80),
        'equipment': '小功率挂机',
        'load': '2.5kW',
    },
    {
        'name': '厨房专用区',
        'rooms': ['厨房'],
        'color': (255, 152, 0, 80),
        'equipment': '厨房专用空调',
        'load': '3.5kW',
    },
    {
        'name': '卫浴区',
        'rooms': ['公共卫生间'],
        'color': (0, 188, 212, 100),
        'equipment': '卫浴专用空调',
        'load': '1.5kW',
    },
    {
        'name': '私密休息区',
        'rooms': ['客卧'],
        'color': (76, 175, 80, 80),
        'equipment': '分体挂机',
        'load': '3.0kW',
    },
    {
        'name': '过渡区',
        'rooms': ['衣帽间'],
        'color': (139, 195, 74, 70),
        'equipment': '与客卧共享',
        'load': '-',
    },
    {
        'name': '楼梯间',
        'rooms': ['楼梯间'],
        'color': (158, 158, 158, 70),
        'equipment': '与餐厅共享',
        'load': '-',
    },
    {
        'name': '设备区',
        'rooms': ['设备间'],
        'color': (200, 200, 200, 60),
        'equipment': '不设空调',
        'load': '-',
    },
]

# ============================================================
# 地暖分区方案
# ============================================================
heat_zones = [
    {
        'name': '水地暖-公共区',
        'rooms': ['客厅', '餐厅', '入户门厅'],
        'color': (103, 58, 183, 80),
        'pipe': 'PE-RT管',
        'spacing': '200mm',
    },
    {
        'name': '水地暖-休息区',
        'rooms': ['客卧'],
        'color': (156, 39, 176, 90),
        'pipe': 'PE-RT管',
        'spacing': '150mm',
    },
    {
        'name': '水地暖-过渡区',
        'rooms': ['衣帽间'],
        'color': (142, 68, 173, 70),
        'pipe': 'PE-RT管',
        'spacing': '150mm',
    },
    {
        'name': '水地暖-楼梯',
        'rooms': ['楼梯间'],
        'color': (121, 85, 72, 70),
        'pipe': 'PE-RT管',
        'spacing': '200mm',
    },
    {
        'name': '电地暖-卫浴',
        'rooms': ['公共卫生间'],
        'color': (255, 87, 34, 100),
        'pipe': '发热电缆',
        'spacing': '100mm',
    },
    {
        'name': '无地暖',
        'rooms': ['厨房', '设备间', '户外露台'],
        'color': (189, 189, 189, 50),
        'pipe': '-',
        'spacing': '-',
    },
]

# ============================================================
# 加载字体
# ============================================================
def get_font(size):
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

font_label = get_font(14)
font_small = get_font(11)
font_title = get_font(22)

# ============================================================
# 绘图函数
# ============================================================
def draw_overlay(img, zones, title, legend_items):
    """绘制叠加示意图"""
    canvas = img.copy()
    
    # 绘制半透明填充
    for zone in zones:
        color = zone['color']
        for room in zone['rooms']:
            if room in rooms:
                x1, y1, x2, y2 = rooms[room]
                overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.rectangle([x1, y1, x2, y2], fill=color)
                canvas = Image.alpha_composite(canvas, overlay)
                draw = ImageDraw.Draw(canvas)
                draw.rectangle([x1, y1, x2, y2], outline=color[:3], width=2)
    
    result = canvas.convert('RGB')
    draw = ImageDraw.Draw(result)
    
    # 绘制房间名称（白色背景黑色字）
    for room_name, (x1, y1, x2, y2) in rooms.items():
        if room_name == '设备间':
            continue
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        bbox = font_label.getbbox(room_name)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([cx - tw//2 - 4, cy - th//2 - 3, 
                        cx + tw//2 + 4, cy + th//2 + 3], 
                       fill=(255, 255, 255, 230))
        draw.text((cx - tw//2, cy - th//2), room_name, 
                  fill=(0, 0, 0), font=font_label)
    
    # 绘制设备标注（带彩色背景）
    for zone in zones:
        color = zone['color'][:3]
        for room in zone['rooms']:
            if room in rooms:
                x1, y1, x2, y2 = rooms[room]
                if 'equipment' in zone:
                    equip = zone['equipment']
                    load = zone.get('load', '')
                    if load and load != '-':
                        label = f"{equip}\n{load}"
                    else:
                        label = equip
                    
                    lines = label.split('\n')
                    line_h = 15
                    th = len(lines) * line_h
                    max_tw = 0
                    for line in lines:
                        bbox = font_small.getbbox(line)
                        max_tw = max(max_tw, bbox[2] - bbox[0])
                    
                    lx = x2 - max_tw - 12
                    ly = y2 - th - 8
                    if lx < x1 + 5:
                        lx = x1 + 5
                    if ly < y1 + 5:
                        ly = y1 + 5
                    
                    # 彩色背景 (RGBA)
                    bg_color = (color[0], color[1], color[2], 230)
                    draw.rectangle([lx - 5, ly - 5, lx + max_tw + 5, ly + th + 5],
                                   fill=bg_color)
                    for i, line in enumerate(lines):
                        draw.text((lx, ly + i * line_h), line, 
                                  fill=(255, 255, 255), font=font_small)
    
    # 标题
    draw.rectangle([10, 10, 420, 45], fill=(50, 50, 50))
    draw.text((15, 14), title, fill=(255, 255, 255), font=font_title)
    
    # 图例
    lx, ly = w - 290, 10
    lh = len(legend_items) * 28 + 40
    draw.rectangle([lx, ly, w - 10, ly + lh], fill=(255, 255, 255, 240))
    draw.rectangle([lx, ly, w - 10, ly + lh], outline=(100, 100, 100), width=1)
    draw.text((lx + 10, ly + 8), "图例:", fill=(0, 0, 0), font=font_label)
    
    for i, (name, color, desc) in enumerate(legend_items):
        yy = ly + 32 + i * 28
        draw.rectangle([lx + 10, yy, lx + 28, yy + 18], fill=color + (220,))
        draw.rectangle([lx + 10, yy, lx + 28, yy + 18], outline=(0, 0, 0), width=1)
        draw.text((lx + 32, yy + 1), f"{name}: {desc}", fill=(0, 0, 0), font=font_small)
    
    return result

# ============================================================
# 生成
# ============================================================
print("生成空调示意图...")
ac_legend = [
    ('公共核心区', (66, 133, 244), '风管机 8.5kW'),
    ('过渡辅助区', (156, 39, 176), '挂机 2.5kW'),
    ('厨房专用区', (255, 152, 0), '厨房空调 3.5kW'),
    ('卫浴区', (0, 188, 212), '卫浴空调 1.5kW'),
    ('私密休息区', (76, 175, 80), '分体挂机 3.0kW'),
    ('过渡区', (139, 195, 74), '与客卧共享'),
    ('楼梯间', (158, 158, 158), '与餐厅共享'),
    ('设备区', (200, 200, 200), '不设空调'),
]
ac_img = draw_overlay(original, ac_zones, "空调系统分区示意图", ac_legend)
ac_img.save('空调新风示意图_生成.png', quality=95)
print("✓ 空调示意图已保存")

print("生成地暖示意图...")
heat_legend = [
    ('水地暖-公共区', (103, 58, 183), 'PE-RT管 200mm'),
    ('水地暖-休息区', (156, 39, 176), 'PE-RT管 150mm'),
    ('水地暖-过渡区', (142, 68, 173), 'PE-RT管 150mm'),
    ('水地暖-楼梯', (121, 85, 72), 'PE-RT管 200mm'),
    ('电地暖-卫浴', (255, 87, 34), '发热电缆 100mm'),
    ('无地暖', (189, 189, 189), '不铺设'),
]
heat_img = draw_overlay(original, heat_zones, "地暖系统分区示意图", heat_legend)
heat_img.save('地暖示意图_生成.png', quality=95)
print("✓ 地暖示意图已保存")

print("\n✅ 全部完成！")
