import sys
sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont

img = Image.open(r"C:\Users\apple\Desktop\成功\试验原图.png")
print(f"原图尺寸: {img.size}")

# 房间坐标 (基于视觉模型精确识别)
rooms = {
    "入户门厅": (50, 150, 480, 460),
    "客厅": (50, 460, 780, 800),
    "餐厅": (540, 580, 780, 720),
    "楼梯间": (540, 230, 780, 480),
    "公共卫生间": (800, 230, 1020, 350),
    "西厨中岛区": (800, 350, 1020, 600),
    "封闭厨房": (1030, 230, 1200, 350),
    "设备间": (800, 160, 1020, 230),
    "客卧": (800, 720, 1200, 970),
    "客卧衣帽间": (800, 600, 1020, 720),
    "露台": (150, 810, 1040, 970),
}

# ========== 空调示意图 ==========
ac_config = {
    "客厅": {"color": (70, 130, 220, 60), "label": "公共核心区", "device": "风管机 8.5kW", "edge": (70, 130, 220, 180)},
    "餐厅": {"color": (70, 130, 220, 60), "label": "", "device": "", "edge": (70, 130, 220, 180)},
    "入户门厅": {"color": (240, 200, 80, 60), "label": "过渡辅助区", "device": "挂机 2.5kW", "edge": (240, 200, 80, 180)},
    "西厨中岛区": {"color": (240, 200, 80, 60), "label": "", "device": "", "edge": (240, 200, 80, 180)},
    "客卧衣帽间": {"color": (240, 200, 80, 60), "label": "", "device": "", "edge": (240, 200, 80, 180)},
    "封闭厨房": {"color": (220, 60, 60, 60), "label": "厨房专用区", "device": "厨房空调 3.5kW", "edge": (220, 60, 60, 180)},
    "公共卫生间": {"color": (60, 200, 200, 60), "label": "卫浴区", "device": "卫浴空调 1.5kW", "edge": (60, 200, 200, 180)},
    "客卧": {"color": (80, 200, 80, 60), "label": "私密休息区", "device": "分体挂机 3.0kW", "edge": (80, 200, 80, 180)},
    "楼梯间": {"color": (160, 100, 200, 60), "label": "楼梯间", "device": "与餐厅共享", "edge": (160, 100, 200, 180)},
}

img_ac = img.copy()
draw_ac = ImageDraw.Draw(img_ac, 'RGBA')
try:
    font = ImageFont.truetype("msyh.ttc", 11)
    font_sm = ImageFont.truetype("msyh.ttc", 9)
except:
    font = ImageFont.load_default()
    font_sm = font

for room, cfg in ac_config.items():
    if room in rooms:
        x1, y1, x2, y2 = rooms[room]
        draw_ac.rectangle([x1, y1, x2, y2], fill=cfg["color"], outline=cfg["edge"], width=2)
        cx, cy = (x1+x2)//2, (y1+y2)//2
        if cfg["label"]:
            bbox = draw_ac.textbbox((0,0), cfg["label"], font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw_ac.rectangle([cx-tw//2-3, cy-th//2-3, cx+tw//2+3, cy+th//2+3], fill=(255,255,255,200))
            draw_ac.text((cx, cy), cfg["label"], fill=cfg["edge"], font=font, anchor="mm")
        if cfg["device"]:
            draw_ac.text((cx, cy+14), cfg["device"], fill=(60,60,60), font=font_sm, anchor="mm")

# 图例
legend_items = [
    ("公共核心区", (70,130,220)), ("过渡辅助区", (240,200,80)),
    ("厨房专用区", (220,60,60)), ("卫浴区", (60,200,200)),
    ("私密休息区", (80,200,80)), ("楼梯间", (160,100,200)),
]
lx, ly = 10, img.size[1]-150
draw_ac.rectangle([lx-5, ly-5, lx+130, ly+len(legend_items)*22+5], fill=(255,255,255,220))
draw_ac.text((lx, ly), "空调系统分区", fill=(0,0,0), font=font)
for i, (name, color) in enumerate(legend_items):
    draw_ac.rectangle([lx, ly+18+i*22, lx+15, ly+30+i*22], fill=color, outline=(0,0,0))
    draw_ac.text((lx+20, ly+18+i*22), name, fill=(0,0,0), font=font_sm)

ac_path = r"C:\Users\apple\Desktop\成功\空调新风示意图_v1.png"
img_ac.save(ac_path, quality=95)
print(f"空调示意图已保存: {ac_path}")

# ========== 地暖示意图 ==========
floor_config = {
    "客厅": {"color": (220,120,180,60), "label": "水地暖-公共区", "info": "PE-RT φ16", "edge": (220,120,180,180)},
    "餐厅": {"color": (220,120,180,60), "label": "", "info": "", "edge": (220,120,180,180)},
    "入户门厅": {"color": (220,120,180,60), "label": "", "info": "", "edge": (220,120,180,180)},
    "西厨中岛区": {"color": (220,120,180,60), "label": "", "info": "", "edge": (220,120,180,180)},
    "客卧": {"color": (180,80,140,60), "label": "水地暖-休息区", "info": "PE-RT φ16", "edge": (180,80,140,180)},
    "客卧衣帽间": {"color": (180,80,140,60), "label": "", "info": "", "edge": (180,80,140,180)},
    "公共卫生间": {"color": (240,150,60,60), "label": "电地暖-卫浴", "info": "发热电缆", "edge": (240,150,60,180)},
    "封闭厨房": {"color": (200,200,200,60), "label": "无地暖", "info": "", "edge": (200,200,200,180)},
    "设备间": {"color": (200,200,200,60), "label": "", "info": "", "edge": (200,200,200,180)},
    "露台": {"color": (200,200,200,60), "label": "", "info": "", "edge": (200,200,200,180)},
}

img_floor = img.copy()
draw_floor = ImageDraw.Draw(img_floor, 'RGBA')

for room, cfg in floor_config.items():
    if room in rooms:
        x1, y1, x2, y2 = rooms[room]
        draw_floor.rectangle([x1, y1, x2, y2], fill=cfg["color"], outline=cfg["edge"], width=2)
        cx, cy = (x1+x2)//2, (y1+y2)//2
        if cfg["label"]:
            bbox = draw_floor.textbbox((0,0), cfg["label"], font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw_floor.rectangle([cx-tw//2-3, cy-th//2-3, cx+tw//2+3, cy+th//2+3], fill=(255,255,255,200))
            draw_floor.text((cx, cy), cfg["label"], fill=cfg["edge"], font=font, anchor="mm")
        if cfg["info"]:
            draw_floor.text((cx, cy+14), cfg["info"], fill=(60,60,60), font=font_sm, anchor="mm")

legend_floor = [
    ("水地暖-公共区", (220,120,180)), ("水地暖-休息区", (180,80,140)),
    ("电地暖-卫浴", (240,150,60)), ("无地暖", (200,200,200)),
]
draw_floor.rectangle([lx-5, ly-5, lx+130, ly+len(legend_floor)*22+5], fill=(255,255,255,220))
draw_floor.text((lx, ly), "地暖系统分区", fill=(0,0,0), font=font)
for i, (name, color) in enumerate(legend_floor):
    draw_floor.rectangle([lx, ly+18+i*22, lx+15, ly+30+i*22], fill=color, outline=(0,0,0))
    draw_floor.text((lx+20, ly+18+i*22), name, fill=(0,0,0), font=font_sm)

floor_path = r"C:\Users\apple\Desktop\成功\地暖示意图_v1.png"
img_floor.save(floor_path, quality=95)
print(f"地暖示意图已保存: {floor_path}")
print("完成！")
