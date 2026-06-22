# -*- coding: utf-8 -*-
"""
基于视觉模型精确识别的坐标，生成空调和地暖示意图
"""

from PIL import Image, ImageDraw, ImageFont
import os

# === 路径 ===
BASE_DIR = r"C:\Users\apple\Desktop\成功"
ORIG = os.path.join(BASE_DIR, "试验原图.png")

# === 加载原图 ===
img = Image.open(ORIG).convert("RGBA")
W, H = img.size
print(f"原图尺寸: {W}x{H}")

# === 精确房间坐标（视觉模型识别的像素坐标）===
ROOMS = {
    "客厅":        {"coords": [192, 393, 492, 673], "label_pos": (282, 315)},
    "餐厅":        {"coords": [527, 525, 631, 634], "label_pos": (525, 505)},
    "客卧":        {"coords": [721, 681, 910, 957], "label_pos": (791, 315)},
    "公共卫生间":  {"coords": [655, 221, 828, 294], "label_pos": (721, 275)},
    "厨房":        {"coords": [654, 291, 911, 554], "label_pos": (802, 425)},
    "入户门厅":    {"coords": [190, 109, 344, 209], "label_pos": (190, 100)},
    "楼梯间":      {"coords": [493, 214, 613, 389], "label_pos": (493, 200)},
}

# 计算面积（像素）
def room_area(coords):
    return (coords[2] - coords[0]) * (coords[3] - coords[1])

# ============================================================
# 空调系统分区方案
# ============================================================
AC_ZONES = [
    {
        "name": "公共核心区",
        "rooms": ["客厅", "餐厅"],
        "color": (65, 130, 210, 100),     # 蓝色半透明
        "border": (30, 80, 180, 220),
        "ac_type": "风管机/中央空调",
        "power": "8.5kW",
        "airflow": "1200m³/h",
        "icon": "square",  # 方形室外机
    },
    {
        "name": "过渡辅助区",
        "rooms": ["入户门厅"],
        "color": (160, 100, 200, 100),    # 紫色半透明
        "border": (130, 60, 170, 220),
        "ac_type": "小功率挂机",
        "power": "2.5kW",
        "airflow": "350m³/h",
        "icon": "small",
    },
    {
        "name": "厨房专用区",
        "rooms": ["厨房"],
        "color": (230, 140, 50, 100),     # 橙色半透明
        "border": (200, 110, 30, 220),
        "ac_type": "厨房专用空调",
        "power": "3.5kW",
        "airflow": "500m³/h",
        "icon": "small",
    },
    {
        "name": "卫浴区",
        "rooms": ["公共卫生间"],
        "color": (100, 200, 220, 120),    # 青色半透明
        "border": (60, 170, 190, 220),
        "ac_type": "卫浴专用空调",
        "power": "1.5kW",
        "airflow": "200m³/h",
        "icon": "small",
    },
    {
        "name": "私密休息区",
        "rooms": ["客卧"],
        "color": (80, 190, 120, 100),     # 绿色半透明
        "border": (50, 160, 80, 220),
        "ac_type": "分体挂机",
        "power": "3.0kW",
        "airflow": "450m³/h",
        "icon": "small",
    },
    {
        "name": "楼梯间（与餐厅共享）",
        "rooms": ["楼梯间"],
        "color": (180, 180, 180, 80),     # 灰色半透明
        "border": (150, 150, 150, 200),
        "ac_type": "与餐厅共享",
        "power": "-",
        "airflow": "-",
        "icon": "none",
    },
]

# ============================================================
# 地暖系统分区方案
# ============================================================
HEAT_ZONES = [
    {
        "name": "水地暖-公共区",
        "rooms": ["客厅", "餐厅", "入户门厅"],
        "color": (200, 160, 230, 100),    # 浅紫色
        "border": (160, 120, 200, 220),
        "type": "水地暖",
        "pipe": "PE-RT管 S5级",
        "spacing": "200mm",
        "temp": "进水45°C / 回水35°C",
    },
    {
        "name": "水地暖-休息区",
        "rooms": ["客卧"],
        "color": (170, 120, 210, 120),    # 深紫色
        "border": (140, 80, 190, 220),
        "type": "水地暖",
        "pipe": "PE-RT管 S5级",
        "spacing": "150mm",
        "temp": "进水45°C / 回水35°C",
    },
    {
        "name": "水地暖-楼梯",
        "rooms": ["楼梯间"],
        "color": (160, 150, 140, 100),    # 灰褐色
        "border": (130, 120, 110, 200),
        "type": "水地暖",
        "pipe": "PE-RT管 S5级",
        "spacing": "200mm",
        "temp": "进水45°C / 回水35°C",
    },
    {
        "name": "电地暖-卫浴",
        "rooms": ["公共卫生间"],
        "color": (240, 170, 80, 120),     # 橙色
        "border": (220, 140, 50, 220),
        "type": "电地暖",
        "pipe": "发热电缆",
        "spacing": "100mm",
        "temp": "功率150W/m²",
    },
]

# 无地暖区域
NO_HEAT_ROOMS = ["厨房"]

# ============================================================
# 尝试加载中文字体
# ============================================================
def get_font(size):
    font_paths = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

font_title = get_font(22)
font_label = get_font(14)
font_small = get_font(12)
font_detail = get_font(11)

# ============================================================
# 绘制函数
# ============================================================
def draw_zones(img, zones, title, no_heat_rooms=None, filename="output.png"):
    canvas = img.copy()
    draw = ImageDraw.Draw(canvas)

    # 1. 绘制各分区颜色填充
    for zone in zones:
        color = zone["color"]
        border = zone["border"]
        for room_name in zone["rooms"]:
            if room_name in ROOMS:
                c = ROOMS[room_name]["coords"]
                # 半透明填充
                overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
                od = ImageDraw.Draw(overlay)
                od.rectangle(c, fill=color)
                canvas = Image.alpha_composite(canvas, overlay)
                draw = ImageDraw.Draw(canvas)
                # 边框
                draw.rectangle(c, outline=border[:3], width=2)

    # 2. 无地暖/无空调区域标记
    if no_heat_rooms:
        for room_name in no_heat_rooms:
            if room_name in ROOMS:
                c = ROOMS[room_name]["coords"]
                # 画斜线表示无供暖
                for i in range(c[0], c[2], 12):
                    draw.line([(i, c[1]), (min(i + (c[3]-c[1]), c[2]), c[3])],
                              fill=(200, 200, 200, 100), width=1)

    # 3. 房间名称标注（在原图文字附近，不遮挡）
    for room_name, info in ROOMS.items():
        c = info["coords"]
        # 房间中心点
        cx = (c[0] + c[2]) // 2
        cy = (c[1] + c[3]) // 2
        # 小标签背景
        bbox = font_small.getbbox(room_name)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # 绘制房间名称（白色背景黑色字）
        draw.rectangle([cx - tw//2 - 3, cy - th//2 - 2, cx + tw//2 + 3, cy + th//2 + 2],
                        fill=(255, 255, 255, 200))
        draw.text((cx - tw//2, cy - th//2), room_name, fill=(0, 0, 0), font=font_small)

    # 4. 图例区域（右侧）
    legend_x = W - 280
    legend_y = 30
    # 图例背景
    draw.rectangle([legend_x - 10, legend_y - 5, W - 5, legend_y + 30 * len(zones) + 80],
                    fill=(255, 255, 255, 230), outline=(0, 0, 0), width=1)
    draw.text((legend_x, legend_y), "图例", fill=(0, 0, 0), font=font_title)
    legend_y += 30

    for zone in zones:
        color = zone["color"]
        # 色块
        draw.rectangle([legend_x, legend_y, legend_x + 20, legend_y + 16],
                        fill=color[:3], outline=(0, 0, 0), width=1)
        # 文字
        draw.text((legend_x + 25, legend_y - 2), zone["name"], fill=(0, 0, 0), font=font_label)
        legend_y += 22
        # 详细信息
        if "ac_type" in zone:
            detail = f"  {zone['ac_type']} | {zone['power']} | {zone['airflow']}"
        else:
            detail = f"  {zone['type']} | {zone['pipe']} | 间距{zone['spacing']}"
        draw.text((legend_x + 25, legend_y - 4), detail, fill=(80, 80, 80), font=font_detail)
        legend_y += 22

    # 5. 标题
    draw.rectangle([10, 5, 300, 35], fill=(255, 255, 255, 200))
    draw.text((15, 8), title, fill=(0, 0, 0), font=font_title)

    # 保存
    output = os.path.join(BASE_DIR, filename)
    canvas = canvas.convert("RGB")
    canvas.save(output, quality=95)
    print(f"✅ 已生成: {output}")
    return output


# ============================================================
# 执行
# ============================================================

# 生成空调示意图
draw_zones(
    img, AC_ZONES,
    title="空调系统分区示意图（精确版）",
    no_heat_rooms=None,
    filename="空调新风示意图_精确版.png"
)

# 生成地暖示意图
draw_zones(
    img, HEAT_ZONES,
    title="地暖系统分区示意图（精确版）",
    no_heat_rooms=NO_HEAT_ROOMS,
    filename="地暖示意图_精确版.png"
)

print("\n全部完成！")
