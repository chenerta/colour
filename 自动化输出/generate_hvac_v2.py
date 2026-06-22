"""
基于试验原图生成空调和地暖示意图 - 修复版
"""
from PIL import Image, ImageDraw, ImageFont
import os

# 加载原图
img_path = '试验原图.png'
original = Image.open(img_path).convert('RGBA')
w, h = original.size
print(f"原图尺寸: {w}x{h}")

# ============================================================
# 房间区域定义 (基于视觉识别结果的像素坐标)
# ============================================================
rooms = {
    '入户门厅':    (80, 120, 280, 250),
    '设备间':      (80, 30, 280, 120),
    '衣帽间':      (280, 180, 480, 350),
    '楼梯间':      (440, 180, 640, 420),
    '客厅':        (80, 380, 480, 680),
    '餐厅':        (480, 420, 700, 680),
    '公共卫生间':  (700, 30, 950, 250),
    '西厨中岛':    (700, 250, 950, 480),
    '封闭厨房':    (700, 480, 950, 650),
    '客卧':        (700, 650, 950, 900),
    '客卧衣帽间':  (700, 580, 850, 650),
    '户外露台':    (80, 680, 700, 950),
}

# ============================================================
# 空调分区方案 - 优化版
# ============================================================
ac_zones = {
    '公共核心区': {
        'rooms': ['客厅', '餐厅'],
        'color': (66, 133, 244, 90),   # 半透明蓝色
        'equipment': '风管机/中央空调',
        'load': '8.5kW',
        'airflow': '侧送下回',
    },
    '过渡辅助区': {
        'rooms': ['入户门厅', '衣帽间'],
        'color': (156, 39, 176, 70),    # 半透明紫色
        'equipment': '小功率挂机',
        'load': '2.5kW',
        'airflow': '侧送侧回',
    },
    '厨房专用区': {
        'rooms': ['西厨中岛', '封闭厨房'],
        'color': (255, 152, 0, 80),     # 半透明橙色
        'equipment': '厨房专用空调',
        'load': '3.5kW',
        'airflow': '抗油污设计',
    },
    '卫浴区': {
        'rooms': ['公共卫生间'],
        'color': (0, 188, 212, 80),     # 半透明青色
        'equipment': '卫浴专用空调',
        'load': '1.5kW',
        'airflow': '除湿功能',
    },
    '私密休息区': {
        'rooms': ['客卧'],
        'color': (76, 175, 80, 80),     # 半透明绿色
        'equipment': '分体挂机',
        'load': '3.0kW',
        'airflow': '侧送下回',
    },
    '客卧衣帽间': {
        'rooms': ['客卧衣帽间'],
        'color': (139, 195, 74, 70),    # 浅绿色
        'equipment': '与客卧共享',
        'load': '共享',
        'airflow': '自然对流',
    },
    '楼梯间': {
        'rooms': ['楼梯间'],
        'color': (158, 158, 158, 60),   # 半透明灰色
        'equipment': '与餐厅共享',
        'load': '共享',
        'airflow': '自然对流',
    },
}

# ============================================================
# 地暖分区方案 - 优化版
# ============================================================
floor_heat_zones = {
    '水地暖-公共区': {
        'rooms': ['客厅', '餐厅', '入户门厅'],
        'color': (103, 58, 183, 80),    # 半透明深紫色
        'type': '水地暖',
        'pipe': 'PE-RT管',
        'spacing': '200mm',
    },
    '水地暖-休息区': {
        'rooms': ['客卧'],
        'color': (156, 39, 176, 80),    # 半透明紫色
        'type': '水地暖',
        'pipe': 'PE-RT管',
        'spacing': '150mm',
    },
    '水地暖-客卧衣帽间': {
        'rooms': ['客卧衣帽间'],
        'color': (142, 68, 173, 70),    # 中紫色
        'type': '水地暖',
        'pipe': 'PE-RT管',
        'spacing': '150mm',
    },
    '水地暖-楼梯': {
        'rooms': ['楼梯间'],
        'color': (121, 85, 72, 70),     # 半透明棕色
        'type': '水地暖',
        'pipe': 'PE-RT管',
        'spacing': '200mm',
    },
    '电地暖-卫浴': {
        'rooms': ['公共卫生间'],
        'color': (255, 87, 34, 90),     # 半透明橙红色
        'type': '电地暖',
        'pipe': '发热电缆',
        'spacing': '100mm',
    },
    '无地暖': {
        'rooms': ['西厨中岛', '封闭厨房', '设备间', '户外露台'],
        'color': (189, 189, 189, 50),   # 半透明浅灰
        'type': '无地暖',
        'pipe': '-',
        'spacing': '-',
    },
}

# ============================================================
# 绘图函数 - 优化版
# ============================================================
def create_overlay_diagram(base_img, zones, title, legend_items):
    """创建叠加示意图"""
    canvas = base_img.copy()
    overlay = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    # 绘制每个区域的半透明填充
    for zone_name, zone_info in zones.items():
        color = zone_info['color']
        for room_name in zone_info['rooms']:
            if room_name in rooms:
                x1, y1, x2, y2 = rooms[room_name]
                draw.rectangle([x1, y1, x2, y2], fill=color)
                draw.rectangle([x1, y1, x2, y2], outline=color[:3], width=2)
    
    # 合并图层
    canvas = Image.alpha_composite(canvas, overlay)
    result = canvas.convert('RGB')
    draw_final = ImageDraw.Draw(result)
    
    # 加载字体
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
        font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 12)
        font_title = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)
    except:
        try:
            font = ImageFont.truetype("msyh.ttc", 16)
            font_small = ImageFont.truetype("msyh.ttc", 12)
            font_title = ImageFont.truetype("msyh.ttc", 24)
        except:
            font = ImageFont.load_default()
            font_small = font
            font_title = font
    
    # 绘制房间名称标注（带白色背景）
    for room_name, (x1, y1, x2, y2) in rooms.items():
        if room_name in ['设备间', '户外露台']:
            continue
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        bbox = draw_final.textbbox((0, 0), room_name, font=font_small)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw_final.rectangle([cx - tw//2 - 4, cy - th//2 - 4, 
                             cx + tw//2 + 4, cy + th//2 + 4], 
                            fill=(255, 255, 255, 220))
        draw_final.text((cx - tw//2, cy - th//2), room_name, 
                      fill=(0, 0, 0), font=font_small)
    
    # 绘制设备标注（放在房间右下角，带彩色背景）
    for zone_name, zone_info in zones.items():
        color = zone_info['color'][:3]
        for room_name in zone_info['rooms']:
            if room_name in rooms and 'equipment' in zone_info:
                x1, y1, x2, y2 = rooms[room_name]
                equip = zone_info['equipment']
                load_val = zone_info.get('load', '')
                if load_val and load_val != '共享':
                    label = f"{equip}\n{load_val}"
                else:
                    label = equip
                
                lines = label.split('\n')
                line_height = 16
                th = len(lines) * line_height
                max_tw = 0
                for line in lines:
                    bbox = draw_final.textbbox((0, 0), line, font=font_small)
                    max_tw = max(max_tw, bbox[2] - bbox[0])
                
                label_x = x2 - max_tw - 15
                label_y = y2 - th - 10
                
                # 确保标注在房间内
                if label_x < x1 + 5:
                    label_x = x1 + 5
                if label_y < y1 + 5:
                    label_y = y1 + 5
                
                draw_final.rectangle([label_x - 6, label_y - 6, 
                                     label_x + max_tw + 6, label_y + th + 6], 
                                    fill=color + (230,))
                
                for i, line in enumerate(lines):
                    draw_final.text((label_x, label_y + i * line_height), line, 
                                  fill=(255, 255, 255), font=font_small)
    
    # 绘制标题（左上角）
    draw_final.rectangle([10, 10, 450, 50], fill=(50, 50, 50))
    draw_final.text((20, 15), title, fill=(255, 255, 255), font=font_title)
    
    # 绘制图例（右上角）
    legend_x, legend_y = w - 300, 10
    legend_h = len(legend_items) * 32 + 45
    draw_final.rectangle([legend_x, legend_y, w - 10, legend_y + legend_h], 
                        fill=(255, 255, 255, 235))
    draw_final.rectangle([legend_x, legend_y, w - 10, legend_y + legend_h], 
                        outline=(100, 100, 100), width=1)
    draw_final.text((legend_x + 10, legend_y + 8), "图例:", fill=(0, 0, 0), font=font)
    
    for i, (name, color, desc) in enumerate(legend_items):
        y = legend_y + 35 + i * 30
        draw_final.rectangle([legend_x + 10, y, legend_x + 30, y + 22], 
                            fill=color + (220,))
        draw_final.rectangle([legend_x + 10, y, legend_x + 30, y + 22], 
                            outline=(0, 0, 0), width=1)
        draw_final.text((legend_x + 35, y + 3), f"{name}: {desc}", 
                      fill=(0, 0, 0), font=font_small)
    
    return result

# ============================================================
# 生成空调示意图
# ============================================================
print("正在生成空调示意图...")
ac_legend = [
    ('公共核心区', (66, 133, 244), '风管机 8.5kW'),
    ('过渡辅助区', (156, 39, 176), '小功率挂机 2.5kW'),
    ('厨房专用区', (255, 152, 0), '厨房专用 3.5kW'),
    ('卫浴区', (0, 188, 212), '卫浴专用 1.5kW'),
    ('私密休息区', (76, 175, 80), '分体挂机 3.0kW'),
    ('客卧衣帽间', (139, 195, 74), '与客卧共享'),
    ('楼梯间', (158, 158, 158), '与餐厅共享'),
]

ac_result = create_overlay_diagram(original, ac_zones, 
                                   "空调系统分区示意图", ac_legend)
ac_path = '空调新风示意图_生成.png'
ac_result.save(ac_path, quality=95)
print(f"空调示意图已保存: {ac_path}")

# ============================================================
# 生成地暖示意图
# ============================================================
print("正在生成地暖示意图...")
fh_legend = [
    ('水地暖-公共区', (103, 58, 183), 'PE-RT管 200mm间距'),
    ('水地暖-休息区', (156, 39, 176), 'PE-RT管 150mm间距'),
    ('水地暖-衣帽间', (142, 68, 173), 'PE-RT管 150mm间距'),
    ('水地暖-楼梯', (121, 85, 72), 'PE-RT管 200mm间距'),
    ('电地暖-卫浴', (255, 87, 34), '发热电缆 100mm间距'),
    ('无地暖', (189, 189, 189), '不铺设'),
]

fh_result = create_overlay_diagram(original, floor_heat_zones, 
                                   "地暖系统分区示意图", fh_legend)
fh_path = '地暖示意图_生成.png'
fh_result.save(fh_path, quality=95)
print(f"地暖示意图已保存: {fh_path}")

print("\n✅ 生成完成！")
print(f"空调示意图: {os.path.abspath(ac_path)}")
print(f"地暖示意图: {os.path.abspath(fh_path)}")
