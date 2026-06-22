# -*- coding: utf-8 -*-
"""
暖通示意图自动生成 v3
方法：先用vision理解图纸，提取精确房间坐标，再叠加暖通方案
这模拟了暖通工程师的工作流：先看懂图纸 → 再做方案
"""
from PIL import Image, ImageDraw, ImageFont
import os

# ============================================================
# 第一步：理解图纸 —— 每层的房间数据（vision分析结果）
# 坐标系：渲染图左上角为原点 (0,0)
# 格式：(x1, y1, x2, y2) 左上角 → 右下角
# ============================================================

FLOORS = {
    "2F": {
        "title": "3F平面布置图（主卧套房）",
        "page": 2,
        "rooms": {
            "衣帽间":   {"bbox": (312, 136, 490, 408), "type": "衣帽间"},
            "楼梯厅":   {"bbox": (498, 136, 723, 408), "type": "楼梯厅"},
            "卧室A":    {"bbox": (273, 412, 852, 806), "type": "主卧"},
            "主卫":     {"bbox": (728, 136, 852, 408), "type": "卫生间"},
        }
    },
    "2F_real": {
        "title": "2F平面布置图（卧室层）",
        "page": 3,
        "rooms": {
            "卧室B":       {"bbox": (216, 139, 493, 394), "type": "卧室"},
            "卧室A":       {"bbox": (215, 588, 491, 855), "type": "卧室"},
            "卧室C":       {"bbox": (621, 499, 839, 853), "type": "卧室"},
            "北侧卫生间":  {"bbox": (741, 141, 838, 392), "type": "卫生间"},
            "南侧卫生间":  {"bbox": (500, 500, 637, 853), "type": "卫生间"},
            "楼梯厅":      {"bbox": (492, 140, 738, 458), "type": "楼梯厅"},
        }
    },
    "1F": {
        "title": "1F平面布置图（起居层）",
        "page": 4,
        "rooms": {
            "庭院花园":  {"bbox": (107, 202, 320, 720), "type": "庭院"},
            "休闲区":    {"bbox": (335, 202, 560, 720), "type": "客厅"},
            "楼梯厅":    {"bbox": (575, 202, 720, 540), "type": "楼梯厅"},
            "餐厅":      {"bbox": (435, 570, 645, 720), "type": "餐厅"},
            "厨房":      {"bbox": (670, 557, 850, 720), "type": "厨房"},
            "卫生间":    {"bbox": (730, 202, 850, 350), "type": "卫生间"},
        }
    },
    "B1": {
        "title": "-1F平面布置图（地下活动层）",
        "page": 5,
        "rooms": {
            "影音室":    {"bbox": (300, 70, 630, 260), "type": "影音室"},
            "品茶区":    {"bbox": (630, 70, 870, 260), "type": "品茶区"},
            "书房":      {"bbox": (290, 270, 460, 350), "type": "书房"},
            "楼梯厅":    {"bbox": (340, 350, 580, 520), "type": "楼梯厅"},
            "娱乐区":    {"bbox": (600, 350, 870, 660), "type": "娱乐区"},
            "卫生间":    {"bbox": (290, 660, 420, 750), "type": "卫生间"},
            "储藏间":    {"bbox": (290, 760, 420, 850), "type": "储藏间"},
            "手工区":    {"bbox": (470, 700, 640, 850), "type": "手工区"},
        }
    },
    "B2": {
        "title": "-2F平面布置图（车库层）",
        "page": 6,
        "rooms": {
            "娱乐区":   {"bbox": (51, 237, 310, 720), "type": "娱乐区"},
            "钢琴区":   {"bbox": (310, 237, 501, 405), "type": "钢琴区"},
            "客厅":     {"bbox": (310, 405, 761, 720), "type": "客厅"},
            "卫生间":   {"bbox": (501, 237, 674, 390), "type": "卫生间"},
            "鞋帽间":   {"bbox": (550, 515, 635, 670), "type": "鞋帽间"},
            "车库":     {"bbox": (763, 237, 945, 722), "type": "车库"},
        }
    },
}

# ============================================================
# 第二步：暖通方案规则 —— 基于房间功能的自动匹配
# 暖通工程师的思路：
#   客厅/餐厅/休闲区 → 公共核心区 → 大功率风管机
#   卧室 → 私密休息区 → 分体/风管机
#   厨房 → 专用空调（油烟大，独立系统）
#   卫浴 → 专用空调（潮湿环境）
#   影音室 → 专用空调（密闭空间，独立温控）
#   楼梯/过道 → 过渡区，共享
#   户外 → 不设空调
# ============================================================

AC_RULES = {
    # (分区名, 设备类型, 功率, 颜色RGBA)
    "客厅":     ("公共核心区", "风管机", "8.5kW", (66, 133, 244, 100)),
    "休闲区":   ("公共核心区", "风管机", "8.5kW", (66, 133, 244, 100)),
    "餐厅":     ("公共核心区", "风管机", "6.5kW", (66, 133, 244, 100)),
    "品茶区":   ("公共核心区", "风管机", "5.0kW", (66, 133, 244, 95)),
    "娱乐区":   ("公共核心区", "风管机", "5.0kW", (66, 133, 244, 95)),
    "钢琴区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 90)),
    "厨房":     ("厨房专用区", "厨房空调", "3.5kW", (255, 152, 0, 100)),
    "卫生间":   ("卫浴区", "卫浴空调", "1.5kW", (0, 188, 212, 110)),
    "主卫":     ("卫浴区", "卫浴空调", "1.5kW", (0, 188, 212, 110)),
    "主卧":     ("私密休息区", "风管机", "5.0kW", (76, 175, 80, 100)),
    "卧室":     ("私密休息区", "分体挂机", "3.5kW", (76, 175, 80, 100)),
    "书房":     ("私密休息区", "分体挂机", "2.5kW", (76, 175, 80, 95)),
    "影音室":   ("专用区", "专用空调", "4.0kW", (156, 39, 176, 100)),
    "衣帽间":   ("过渡区", "与卧室共享", "-", (139, 195, 74, 70)),
    "鞋帽间":   ("过渡区", "与客厅共享", "-", (139, 195, 74, 70)),
    "楼梯厅":   ("过渡区", "与相邻区共享", "-", (158, 158, 158, 70)),
    "储藏间":   ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "设备间":   ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "庭院":     ("户外区", "不设空调", "-", (200, 200, 200, 50)),
    "车库":     ("设备区", "不设空调", "-", (200, 200, 200, 60)),
    "手工区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 90)),
    "酒柜":     ("过渡区", "-", "-", (180, 180, 180, 50)),
    "露台":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "健身":     ("设备区", "不设空调", "-", (200, 200, 200, 50)),
}

HEAT_RULES = {
    # (分区名, 管材, 间距, 颜色RGBA)
    "客厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "休闲区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "餐厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 90)),
    "品茶区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "娱乐区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "钢琴区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "主卧":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 100)),
    "卧室":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 100)),
    "书房":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "影音室":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "卫生间":   ("电地暖-卫浴", "发热电缆", "100mm", (255, 87, 34, 110)),
    "主卫":     ("电地暖-卫浴", "发热电缆", "100mm", (255, 87, 34, 110)),
    "楼梯厅":   ("水地暖-楼梯", "PE-RT管", "200mm", (121, 85, 72, 80)),
    "衣帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 70)),
    "鞋帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 70)),
    "厨房":     ("无地暖", "-", "-", (189, 189, 189, 60)),
    "储藏间":   ("无地暖", "-", "-", (189, 189, 189, 50)),
    "设备间":   ("无地暖", "-", "-", (189, 189, 189, 50)),
    "庭院":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "车库":     ("无地暖", "-", "-", (189, 189, 189, 50)),
    "手工区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 85)),
    "酒柜":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "露台":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "健身":     ("无地暖", "-", "-", (189, 189, 189, 40)),
}

# ============================================================
# 工具函数
# ============================================================
def get_font(size):
    for fp in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except:
                continue
    return ImageFont.load_default()

def draw_overlay(base_img, rooms_data, title, legend_items):
    """在底图上叠加暖通分区"""
    canvas = base_img.copy().convert("RGBA")
    w, h = canvas.size

    font_title = get_font(20)
    font_label = get_font(14)
    font_small = get_font(11)

    for room_name, room_info in rooms_data.items():
        bbox = room_info["bbox"]
        rule = room_info["rule"]
        zone_name = rule[0]
        equip = rule[1]
        load = rule[2]
        color = rule[3]

        x0, y0, x1, y1 = bbox
        bw = x1 - x0
        bh = y1 - y0
        if bw < 20 or bh < 20:
            continue

        # 半透明填充
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle(bbox, fill=color)
        canvas = Image.alpha_composite(canvas, overlay)

        draw = ImageDraw.Draw(canvas)
        draw.rectangle(bbox, outline=color[:3], width=2)

        # 房间名称（居中，白底黑字）
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        bbox_t = font_label.getbbox(room_name)
        tw = bbox_t[2] - bbox_t[0]
        th = bbox_t[3] - bbox_t[1]

        # 名称标签
        lx = cx - tw / 2 - 4
        ly = cy - th / 2 - 12
        draw.rectangle([lx, ly, lx + tw + 8, ly + th + 4],
                        fill=(255, 255, 255, 230), outline=(80, 80, 80), width=1)
        draw.text((lx + 4, ly + 2), room_name, fill=(0, 0, 0), font=font_label)

        # 设备标注（带彩色背景）
        if equip and equip != "-":
            if load and load != "-":
                elabel = f"{equip} {load}"
            else:
                elabel = equip
            bbox_e = font_small.getbbox(elabel)
            ew = bbox_e[2] - bbox_e[0]
            eh = bbox_e[3] - bbox_e[1]
            ex = cx - ew / 2
            ey = ly + th + 10

            # 确保不超出房间边界
            if ex < x0 + 4:
                ex = x0 + 4
            if ey + eh > y1 - 4:
                ey = y1 - eh - 4

            bg = color[:3] + (220,)
            draw.rectangle([ex - 4, ey - 2, ex + ew + 4, ey + eh + 2], fill=bg)
            draw.text((ex, ey), elabel, fill=(255, 255, 255), font=font_small)

    result = canvas.convert("RGB")
    draw = ImageDraw.Draw(result)

    # 标题栏
    draw.rectangle([10, 8, 440, 42], fill=(30, 30, 30))
    draw.text((15, 14), title, fill=(255, 255, 255), font=font_title)

    # 图例
    lx = w - 300
    ly = 8
    lh = len(legend_items) * 26 + 36
    draw.rectangle([lx, ly, w - 8, ly + lh], fill=(255, 255, 255, 230))
    draw.rectangle([lx, ly, w - 8, ly + lh], outline=(100, 100, 100), width=1)
    draw.text((lx + 8, ly + 8), "图例:", fill=(0, 0, 0), font=font_label)

    for i, (name, color, desc) in enumerate(legend_items):
        yy = ly + 32 + i * 26
        draw.rectangle([lx + 8, yy, lx + 26, yy + 18], fill=color + (220,))
        draw.rectangle([lx + 8, yy, lx + 26, yy + 18], outline=(0, 0, 0), width=1)
        draw.text((lx + 30, yy + 1), f"{name}: {desc}", fill=(0, 0, 0), font=font_small)

    return result

# ============================================================
# 主流程
# ============================================================
OUT_DIR = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
IMG_DIR = OUT_DIR

AC_LEGEND = [
    ("公共核心区", (66, 133, 244), "风管机 3.5-8.5kW"),
    ("私密休息区", (76, 175, 80), "分体/风管机 2.5-5kW"),
    ("厨房专用区", (255, 152, 0), "厨房空调 3.5kW"),
    ("卫浴区", (0, 188, 212), "卫浴空调 1.5kW"),
    ("专用区", (156, 39, 176), "专用空调 4kW"),
    ("过渡区", (158, 158, 158), "与相邻区域共享"),
    ("设备区", (200, 200, 200), "不设空调"),
]

HEAT_LEGEND = [
    ("水地暖-公共区", (103, 58, 183), "PE-RT管 200mm"),
    ("水地暖-休息区", (156, 39, 176), "PE-RT管 150mm"),
    ("水地暖-楼梯", (121, 85, 72), "PE-RT管 200mm"),
    ("水地暖-过渡区", (142, 68, 173), "PE-RT管 200mm"),
    ("电地暖-卫浴", (255, 87, 34), "发热电缆 100mm"),
    ("无地暖", (189, 189, 189), "不铺设"),
]

print("=" * 60)
print("暖通示意图自动生成 v3（基于图纸理解）")
print("=" * 60)

for floor_key, floor_data in FLOORS.items():
    page_num = floor_data["page"]
    title = floor_data["title"]
    rooms = floor_data["rooms"]

    # 加载底图
    img_path = os.path.join(IMG_DIR, f"page_{page_num}.png")
    if not os.path.exists(img_path):
        print(f"  ⚠ 底图不存在: {img_path}")
        continue

    base_img = Image.open(img_path)
    print(f"\n{'='*50}")
    print(f"{title} (page_{page_num}.png)")
    print(f"  房间数: {len(rooms)}")
    for name, info in rooms.items():
        print(f"    {name}: {info['bbox']} → {info['type']}")

    # 匹配空调规则
    ac_data = {}
    for name, info in rooms.items():
        room_type = info["type"]
        if room_type in AC_RULES:
            ac_data[name] = {"bbox": info["bbox"], "rule": AC_RULES[room_type]}

    # 匹配地暖规则
    heat_data = {}
    for name, info in rooms.items():
        room_type = info["type"]
        if room_type in HEAT_RULES:
            heat_data[name] = {"bbox": info["bbox"], "rule": HEAT_RULES[room_type]}

    # 生成空调示意图
    if ac_data:
        ac_img = draw_overlay(base_img, ac_data,
                               f"空调系统分区示意图 - {title}", AC_LEGEND)
        ac_path = os.path.join(OUT_DIR, f"空调新风示意图_{floor_key}.png")
        ac_img.save(ac_path, quality=95)
        print(f"  ✅ 空调示意图已保存")

    # 生成地暖示意图
    if heat_data:
        heat_img = draw_overlay(base_img, heat_data,
                                 f"地暖系统分区示意图 - {title}", HEAT_LEGEND)
        heat_path = os.path.join(OUT_DIR, f"地暖示意图_{floor_key}.png")
        heat_img.save(heat_path, quality=95)
        print(f"  ✅ 地暖示意图已保存")

print(f"\n{'='*60}")
print(f"✅ 全部完成！输出目录: {OUT_DIR}")
print(f"{'='*60}")
