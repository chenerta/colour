# -*- coding: utf-8 -*-
"""
暖通示意图全自动生成工具 v2
修复：房间边界推算过于保守的问题
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import os
import json

# ============================================================
# 配置
# ============================================================
PDF_PATH = r"C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf"
OUT_DIR  = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
os.makedirs(OUT_DIR, exist_ok=True)
SCALE = 2.0

FLOOR_PLAN_KEYWORDS = ["平面布置图", "平面图", "布置图", "Floor Plan"]

BOILERPLATE = [
    "圖稱", "TITLE", "工程名稱", "PROJECT", "日期", "DATE",
    "編號", "JOB", "單位", "UNIT", "比例", "SCALE",
    "設計", "DESIGNED", "繪圖", "DRAWN", "核准", "APPROVED",
    "圖面修正", "REVISIONS", "圖號", "DRAWING", "頁數", "NUMBER",
    "版權所有", "請尊重智慧財產權", "凌傑內建築設計有限公司",
    "TEL:", "E-MAIL:", "ADD:", "浙江省", "云水山庄",
    "厘米", "cm", "A3", "1/65", "63", "號", "中）",
]

ROOM_NAME_KEYWORDS = [
    "客厅", "餐厅", "厨房", "卫生间", "卧室", "书房", "影音室",
    "品茶区", "娱乐区", "休闲区", "楼梯厅", "衣帽间", "鞋帽间",
    "储藏间", "设备间", "阳台", "露台", "庭院", "花园", "车库",
    "酒柜", "手工区", "钢琴区", "健身", "过道", "走廊",
    "客卧", "主卧", "次卧", "入户", "门厅",
]

# ============================================================
# 暖通规则表（同v1）
# ============================================================
AC_RULES = {
    "客厅":     ("公共核心区", "风管机/中央空调", "8.5kW", (66, 133, 244, 90)),
    "休闲区":   ("公共核心区", "风管机/中央空调", "8.5kW", (66, 133, 244, 90)),
    "餐厅":     ("公共核心区", "风管机/中央空调", "6.5kW", (66, 133, 244, 90)),
    "品茶区":   ("公共核心区", "风管机/中央空调", "5.0kW", (66, 133, 244, 85)),
    "厨房":     ("厨房专用区", "厨房专用空调", "3.5kW", (255, 152, 0, 90)),
    "卫生间":   ("卫浴区", "卫浴专用空调", "1.5kW", (0, 188, 212, 100)),
    "卧室":     ("私密休息区", "分体挂机", "3.0kW", (76, 175, 80, 90)),
    "主卧":     ("私密休息区", "分体挂机", "4.0kW", (76, 175, 80, 90)),
    "客卧":     ("私密休息区", "分体挂机", "3.0kW", (76, 175, 80, 90)),
    "卧室A":    ("私密休息区", "风管机", "5.0kW", (76, 175, 80, 90)),
    "卧室B":    ("私密休息区", "分体挂机", "3.5kW", (76, 175, 80, 90)),
    "卧室C":    ("私密休息区", "分体挂机", "3.5kW", (76, 175, 80, 90)),
    "书房":     ("私密休息区", "分体挂机", "2.5kW", (76, 175, 80, 85)),
    "影音室":   ("专用区", "专用空调", "4.0kW", (156, 39, 176, 85)),
    "娱乐区":   ("公共核心区", "风管机", "5.0kW", (66, 133, 244, 85)),
    "衣帽间":   ("过渡区", "与相邻区域共享", "-", (139, 195, 74, 60)),
    "鞋帽间":   ("过渡区", "与相邻区域共享", "-", (139, 195, 74, 60)),
    "楼梯厅":   ("过渡区", "与相邻区域共享", "-", (158, 158, 158, 60)),
    "储藏间":   ("设备区", "不设空调", "-", (200, 200, 200, 50)),
    "设备间":   ("设备区", "不设空调", "-", (200, 200, 200, 50)),
    "庭院":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "花园":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "车库":     ("设备区", "不设空调", "-", (200, 200, 200, 50)),
    "酒柜":     ("过渡区", "-", "-", (180, 180, 180, 40)),
    "手工区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 80)),
    "钢琴区":   ("公共核心区", "风管机", "3.5kW", (66, 133, 244, 80)),
    "阳台":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "露台":     ("户外区", "不设空调", "-", (200, 200, 200, 40)),
    "过道":     ("过渡区", "-", "-", (158, 158, 158, 40)),
    "走廊":     ("过渡区", "-", "-", (158, 158, 158, 40)),
}

HEAT_RULES = {
    "客厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 80)),
    "休闲区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 80)),
    "餐厅":     ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 80)),
    "品茶区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 80)),
    "卧室":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "主卧":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "客卧":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "卧室A":    ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "卧室B":    ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "卧室C":    ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 90)),
    "卫生间":   ("电地暖-卫浴", "发热电缆", "100mm", (255, 87, 34, 100)),
    "楼梯厅":   ("水地暖-楼梯", "PE-RT管", "200mm", (121, 85, 72, 70)),
    "影音室":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 75)),
    "娱乐区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 75)),
    "书房":     ("水地暖-休息区", "PE-RT管", "150mm", (156, 39, 176, 80)),
    "厨房":     ("无地暖", "-", "-", (189, 189, 189, 50)),
    "衣帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 60)),
    "鞋帽间":   ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 60)),
    "储藏间":   ("无地暖", "-", "-", (189, 189, 189, 40)),
    "设备间":   ("无地暖", "-", "-", (189, 189, 189, 40)),
    "庭院":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "花园":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "车库":     ("无地暖", "-", "-", (189, 189, 189, 40)),
    "阳台":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "露台":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "酒柜":     ("无地暖", "-", "-", (189, 189, 189, 30)),
    "手工区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 75)),
    "钢琴区":   ("水地暖-公共区", "PE-RT管", "200mm", (103, 58, 183, 75)),
    "过道":     ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 50)),
    "走廊":     ("水地暖-过渡区", "PE-RT管", "200mm", (142, 68, 173, 50)),
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

def is_boilerplate(text):
    for bp in BOILERPLATE:
        if bp in text:
            return True
    return False

def match_room_name(text):
    for kw in ROOM_NAME_KEYWORDS:
        if kw in text:
            return kw
    return None

def match_rule(room_name, rules):
    if room_name in rules:
        return rules[room_name]
    best_match = None
    best_len = 0
    for key in rules:
        if key in room_name or room_name in key:
            if len(key) > best_len:
                best_match = rules[key]
                best_len = len(key)
    return best_match

def is_floor_plan_page(texts):
    all_text = " ".join([t["text"] for t in texts])
    for kw in FLOOR_PLAN_KEYWORDS:
        if kw in all_text:
            return True
    return False

def extract_room_names(texts):
    """提取房间名称，优先取中文名"""
    rooms = {}
    for t in texts:
        txt = t["text"].strip()
        if is_boilerplate(txt):
            continue
        room = match_room_name(txt)
        if room:
            font = t.get("font", "")
            # 中文字体优先
            is_cn_font = any(f in font for f in ["SimSun", "SimHei", "SimKai", "FangSong"])
            if is_cn_font:
                if txt not in rooms:
                    rooms[txt] = {
                        "bbox_pdf": t["bbox"],
                        "size": t["size"],
                        "room_type": room,
                    }
    # 如果中文名不够，补充英文名
    if len(rooms) < 3:
        eng_map = {
            "BEDROOM": "卧室", "BATHROOM": "卫生间", "KITCHEN": "厨房",
            "CLOAKROOM": "衣帽间", "STAIRWELL": "楼梯厅", "GARAGE": "车库",
            "GARDEN": "花园", "DRAWINGROOM": "客厅", "PLAY AREA": "娱乐区",
            "MOVEROOM": "影音室", "STORAGE": "储藏间", "BALCONY": "阳台",
            "STUDY": "书房", "PANTRY": "储藏间", "LOUNGE": "休闲区",
        }
        for t in texts:
            txt = t["text"].strip()
            if is_boilerplate(txt):
                continue
            txt_upper = txt.upper().strip()
            for eng, cn in eng_map.items():
                if eng in txt_upper:
                    if cn not in rooms:
                        rooms[cn] = {
                            "bbox_pdf": t["bbox"],
                            "size": t["size"],
                            "room_type": cn,
                        }
                    break
    return rooms

def find_major_walls(vectors, page_rect):
    """提取主要墙体线条（长线条，可能是承重墙/房间分隔墙）"""
    walls_h = []  # 水平墙
    walls_v = []  # 垂直墙
    
    page_w = page_rect.width
    page_h = page_rect.height
    
    for vtype, x0, y0, x1, y1 in vectors:
        if vtype == "line":
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            # 水平墙：近似水平且足够长
            if dy < 3 and dx > 80:
                walls_h.append((min(x0, x1), y0, max(x0, x1), y0))
            # 垂直墙：近似垂直且足够长
            if dx < 3 and dy > 80:
                walls_v.append((x0, min(y0, y1), x0, max(y0, y1)))
    
    return walls_h, walls_v

def estimate_room_boundary(cx, cy, room_type, walls_h, walls_v, page_rect):
    """基于文字中心点 + 墙体线条，估算房间边界
    
    策略：
    1. 从中心点向四个方向搜索最近的墙体线条
    2. 如果找到墙体，用墙体位置作为边界
    3. 如果没找到，用默认扩展比例
    """
    pw = page_rect.width
    ph = page_rect.height
    
    # 根据房间类型设置默认扩展比例
    size_map = {
        "客厅": (0.28, 0.35),     # 大空间
        "休闲区": (0.25, 0.30),
        "餐厅": (0.20, 0.25),
        "厨房": (0.15, 0.20),
        "卫生间": (0.12, 0.15),
        "卧室": (0.20, 0.25),
        "卧室A": (0.25, 0.30),
        "卧室B": (0.20, 0.25),
        "卧室C": (0.20, 0.25),
        "主卧": (0.25, 0.30),
        "客卧": (0.20, 0.25),
        "书房": (0.18, 0.22),
        "影音室": (0.20, 0.25),
        "娱乐区": (0.22, 0.28),
        "品茶区": (0.18, 0.22),
        "衣帽间": (0.15, 0.18),
        "鞋帽间": (0.12, 0.15),
        "楼梯厅": (0.18, 0.25),
        "储藏间": (0.15, 0.18),
        "设备间": (0.12, 0.15),
        "庭院": (0.28, 0.35),
        "花园": (0.28, 0.35),
        "车库": (0.25, 0.30),
        "酒柜": (0.08, 0.10),
        "手工区": (0.18, 0.22),
        "钢琴区": (0.15, 0.18),
        "阳台": (0.20, 0.12),
        "露台": (0.20, 0.12),
    }
    
    rx, ry = size_map.get(room_type, (0.18, 0.22))
    default_expand_x = pw * rx
    default_expand_y = ph * ry
    
    # 初始边界
    left = cx - default_expand_x
    right = cx + default_expand_x
    bottom = cy - default_expand_y
    top = cy + default_expand_y
    
    # 在墙体中搜索最近的墙来收紧边界
    search_range = default_expand_x * 1.5
    
    # 搜索左侧垂直墙
    for wx, wy0, _, wy1 in walls_v:
        if wx < cx and cx - wx < search_range and wy0 < cy < wy1:
            if wx > left:
                left = wx
    
    # 搜索右侧垂直墙
    for wx, wy0, _, wy1 in walls_v:
        if wx > cx and wx - cx < search_range and wy0 < cy < wy1:
            if wx < right:
                right = wx
    
    # 搜索下方水平墙
    for wx0, wy, wx1, _ in walls_h:
        if wy < cy and cy - wy < search_range * 0.8 and wx0 < cx < wx1:
            if wy > bottom:
                bottom = wy
    
    # 搜索上方水平墙
    for wx0, wy, wx1, _ in walls_h:
        if wy > cy and wy - cy < search_range * 0.8 and wx0 < cx < wx1:
            if wy < top:
                top = wy
    
    # 确保边界合理（最小100pt，最大不超过页面）
    min_size = 80
    if right - left < min_size:
        margin = (min_size - (right - left)) / 2
        left -= margin
        right += margin
    if top - bottom < min_size:
        margin = (min_size - (top - bottom)) / 2
        bottom -= margin
        top += margin
    
    # 限制在页面内
    left = max(left, 40)
    right = min(right, pw - 40)
    bottom = max(bottom, 40)
    top = min(top, ph - 40)
    
    return (left, bottom, right, top)

def resolve_overlaps(boundaries):
    """解决房间边界重叠问题：缩紧重叠区域"""
    names = list(boundaries.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            b1 = boundaries[names[i]]
            b2 = boundaries[names[j]]
            
            # 检查是否重叠
            if (b1[0] < b2[2] and b1[2] > b2[0] and 
                b1[1] < b2[3] and b1[3] > b2[1]):
                # 计算重叠区域
                overlap_x = min(b1[2], b2[2]) - max(b1[0], b2[0])
                overlap_y = min(b1[3], b2[3]) - max(b1[1], b2[1])
                
                if overlap_x > 0 and overlap_y > 0:
                    # 向各自中心收缩一半的重叠量
                    shrink_x = overlap_x / 4
                    shrink_y = overlap_y / 4
                    
                    c1x = (b1[0] + b1[2]) / 2
                    c2x = (b2[0] + b2[2]) / 2
                    c1y = (b1[1] + b1[3]) / 2
                    c2y = (b2[1] + b2[3]) / 2
                    
                    nb1 = list(b1)
                    nb2 = list(b2)
                    
                    if c1x < c2x:
                        nb1[2] -= shrink_x
                        nb2[0] += shrink_x
                    else:
                        nb1[0] += shrink_x
                        nb2[2] -= shrink_x
                    
                    if c1y < c2y:
                        nb1[3] -= shrink_y
                        nb2[1] += shrink_y
                    else:
                        nb1[1] += shrink_y
                        nb2[3] -= shrink_y
                    
                    boundaries[names[i]] = tuple(nb1)
                    boundaries[names[j]] = tuple(nb2)
    
    return boundaries

def pdf_to_image_coords(bbox_pdf, page_h, scale):
    """PDF坐标转图片坐标"""
    x0, y0, x1, y1 = bbox_pdf
    ix0 = x0 * scale
    iy0 = (page_h - y1) * scale
    ix1 = x1 * scale
    iy1 = (page_h - y0) * scale
    return (ix0, iy0, ix1, iy1)

# ============================================================
# 绘图函数
# ============================================================
def draw_overlay(base_img, rooms_with_zones, title, legend_items, page_label):
    canvas = base_img.convert("RGBA")
    w, h = canvas.size
    
    font_title = get_font(20)
    font_label = get_font(14)
    font_small = get_font(11)
    font_zone = get_font(12)
    
    # 绘制各分区
    for room_info in rooms_with_zones:
        zone = room_info["zone"]
        boundary = room_info["boundary_img"]
        
        # 确保坐标有效
        x0, y0, x1, y1 = boundary
        if x1 - x0 < 10 or y1 - y0 < 10:
            continue
        
        # 半透明填充
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle(boundary, fill=zone["color"])
        canvas = Image.alpha_composite(canvas, overlay)
        
        draw = ImageDraw.Draw(canvas)
        draw.rectangle(boundary, outline=zone["color"][:3], width=2)
        
        # 房间名称
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        name = room_info["display_name"]
        bbox = font_label.getbbox(name)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        
        # 白色背景标签
        label_y = cy - th / 2 - 12
        draw.rectangle([cx - tw/2 - 4, label_y - 2, cx + tw/2 + 4, label_y + th + 2],
                        fill=(255, 255, 255, 230), outline=(0, 0, 0), width=1)
        draw.text((cx - tw/2, label_y), name, fill=(0, 0, 0), font=font_label)
        
        # 设备标注
        equip = zone.get("equipment", "")
        load = zone.get("load", "")
        if equip and equip != "-":
            if load and load != "-":
                elabel = f"{equip} {load}"
            else:
                elabel = equip
            bbox_e = font_small.getbbox(elabel)
            ew = bbox_e[2] - bbox_e[0]
            eh = bbox_e[3] - bbox_e[1]
            ex = cx - ew / 2
            ey = label_y + th + 6
            
            # 确保不超出边界
            if ex < x0 + 4:
                ex = x0 + 4
            if ey + eh > y1 - 4:
                ey = y1 - eh - 4
            
            bg = zone["color"][:3] + (220,)
            draw.rectangle([ex - 4, ey - 2, ex + ew + 4, ey + eh + 2], fill=bg)
            draw.text((ex, ey), elabel, fill=(255, 255, 255), font=font_small)
    
    result = canvas.convert("RGB")
    draw = ImageDraw.Draw(result)
    
    # 标题栏
    draw.rectangle([10, 8, 420, 42], fill=(40, 40, 40))
    full_title = f"{title} - {page_label}"
    draw.text((15, 14), full_title, fill=(255, 255, 255), font=font_title)
    
    # 图例
    lx = w - 290
    ly = 8
    lh = len(legend_items) * 26 + 34
    draw.rectangle([lx, ly, w - 8, ly + lh], fill=(255, 255, 255, 230))
    draw.rectangle([lx, ly, w - 8, ly + lh], outline=(100, 100, 100), width=1)
    draw.text((lx + 8, ly + 6), "图例:", fill=(0, 0, 0), font=font_label)
    
    for i, (name, color, desc) in enumerate(legend_items):
        yy = ly + 30 + i * 26
        draw.rectangle([lx + 8, yy, lx + 26, yy + 18], fill=color + (220,))
        draw.rectangle([lx + 8, yy, lx + 26, yy + 18], outline=(0, 0, 0), width=1)
        draw.text((lx + 30, yy + 1), f"{name}: {desc}", fill=(0, 0, 0), font=font_small)
    
    return result

# ============================================================
# 主流程
# ============================================================
print("=" * 60)
print("暖通示意图自动生成工具 v2")
print("=" * 60)

doc = fitz.open(PDF_PATH)
print(f"PDF: {PDF_PATH}")
print(f"页数: {doc.page_count}")

AC_LEGEND = [
    ("公共核心区", (66, 133, 244), "风管机 5-8.5kW"),
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

for page_idx in range(doc.page_count):
    page = doc.load_page(page_idx)
    rect = page.rect
    print(f"\n{'='*50}")
    print(f"第{page_idx+1}页 (PDF: {rect.width:.0f}x{rect.height:.0f}pt)")
    
    # 1. 提取文字
    text_instances = page.get_text("dict")["blocks"]
    all_texts = []
    for block in text_instances:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    txt = span["text"].strip()
                    if txt:
                        all_texts.append({
                            "text": txt,
                            "bbox": list(span["bbox"]),
                            "size": span["size"],
                            "font": span["font"]
                        })
    
    # 2. 判断是否为平面图
    if not is_floor_plan_page(all_texts):
        print("  → 跳过（非平面布置图）")
        continue
    
    # 3. 提取房间名称
    room_names = extract_room_names(all_texts)
    if not room_names:
        print("  → 跳过（未识别到房间名）")
        continue
    
    print(f"  识别到 {len(room_names)} 个房间:")
    for name, info in room_names.items():
        print(f"    {name} ({info['room_type']})")
    
    # 4. 提取主要墙体
    drawings = page.get_drawings()
    vectors = []
    for d in drawings:
        for item in d["items"]:
            if item[0] == "l":
                vectors.append(("line", item[1].x, item[1].y, item[2].x, item[2].y))
            elif item[0] == "re":
                r = item[1]
                vectors.append(("rect", r.x0, r.y0, r.x1, r.y1))
    
    walls_h, walls_v = find_major_walls(vectors, rect)
    print(f"  主要墙体: 水平{len(walls_h)}条, 垂直{len(walls_v)}条")
    
    # 5. 推算房间边界（PDF坐标）
    boundaries = {}
    for name, info in room_names.items():
        bbox = info["bbox_pdf"]
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        boundary = estimate_room_boundary(cx, cy, info["room_type"], walls_h, walls_v, rect)
        boundaries[name] = {
            "boundary_pdf": boundary,
            "center_pdf": (cx, cy),
            "room_type": info["room_type"],
        }
    
    # 6. 解决重叠
    pdf_bounds = {n: b["boundary_pdf"] for n, b in boundaries.items()}
    pdf_bounds = resolve_overlaps(pdf_bounds)
    for n in boundaries:
        boundaries[n]["boundary_pdf"] = pdf_bounds[n]
    
    # 7. 渲染页面
    mat = fitz.Matrix(SCALE, SCALE)
    pix = page.get_pixmap(matrix=mat)
    page_img_path = os.path.join(OUT_DIR, f"page_{page_idx+1}.png")
    pix.save(page_img_path)
    base_img = Image.open(page_img_path)
    
    # 获取页面标题
    page_title = ""
    for t in all_texts:
        if "平面" in t["text"] and "布置" in t["text"]:
            page_title = t["text"]
            break
        elif "平面" in t["text"]:
            page_title = t["text"]
            break
    if not page_title:
        page_title = f"第{page_idx+1}页"
    
    # 8. 生成空调示意图
    ac_rooms = []
    for name, rb in boundaries.items():
        rule = match_rule(rb["room_type"], AC_RULES)
        if rule:
            zone_name, equip, load, color = rule
            boundary_img = pdf_to_image_coords(rb["boundary_pdf"], rect.height, SCALE)
            ac_rooms.append({
                "display_name": name,
                "boundary_img": boundary_img,
                "zone": {"name": zone_name, "color": color, "equipment": equip, "load": load},
            })
    
    if ac_rooms:
        ac_img = draw_overlay(base_img, ac_rooms, "空调系统分区示意图", AC_LEGEND, page_title)
        ac_path = os.path.join(OUT_DIR, f"空调新风示意图_第{page_idx+1}页.png")
        ac_img.save(ac_path, quality=95)
        print(f"  ✅ 空调示意图: {ac_path}")
    
    # 9. 生成地暖示意图
    heat_rooms = []
    for name, rb in boundaries.items():
        rule = match_rule(rb["room_type"], HEAT_RULES)
        if rule:
            zone_name, pipe, spacing, color = rule
            boundary_img = pdf_to_image_coords(rb["boundary_pdf"], rect.height, SCALE)
            heat_rooms.append({
                "display_name": name,
                "boundary_img": boundary_img,
                "zone": {"name": zone_name, "color": color, "equipment": pipe, "load": spacing},
            })
    
    if heat_rooms:
        heat_img = draw_overlay(base_img, heat_rooms, "地暖系统分区示意图", HEAT_LEGEND, page_title)
        heat_path = os.path.join(OUT_DIR, f"地暖示意图_第{page_idx+1}页.png")
        heat_img.save(heat_path, quality=95)
        print(f"  ✅ 地暖示意图: {heat_path}")

doc.close()
print(f"\n{'='*60}")
print(f"✅ 全部完成！输出目录: {OUT_DIR}")
print(f"{'='*60}")
