# -*- coding: utf-8 -*-
"""
暖通示意图全自动生成工具
输入：建筑平面图PDF
输出：空调新风示意图 + 地暖示意图（PNG）

工作流：
1. 用PyMuPDF读取PDF，提取每页文字位置（房间名称锚点）
2. 用PyMuPDF提取矢量路径（墙体线条），用于推算房间边界
3. 结合文字位置 + 矢量路径，自动确定每个房间的矩形边界
4. 按规则表匹配暖通方案（空调分区/地暖分区）
5. 在渲染图上叠加半透明色块 + 文字标注 + 图例
"""
import fitz
from PIL import Image, ImageDraw, ImageFont
import os
import json
import re

# ============================================================
# 配置
# ============================================================
PDF_PATH = r"C:\Users\apple\Desktop\成功\湖滨壹号 Allen郑(1).pdf"
OUT_DIR  = r"C:\Users\apple\Desktop\湖滨壹号_自动化输出"
os.makedirs(OUT_DIR, exist_ok=True)
SCALE = 2.0  # 渲染倍率

# 页面标题中的关键词 → 判断是否为平面布置图
FLOOR_PLAN_KEYWORDS = ["平面布置图", "平面图", "布置图", "Floor Plan"]

# 图框底部样板文字（过滤用）
BOILERPLATE = [
    "圖稱", "TITLE", "工程名稱", "PROJECT", "日期", "DATE",
    "編號", "JOB", "單位", "UNIT", "比例", "SCALE",
    "設計", "DESIGNED", "繪圖", "DRAWN", "核准", "APPROVED",
    "圖面修正", "REVISIONS", "圖號", "DRAWING", "頁數", "NUMBER",
    "版權所有", "請尊重智慧財產權", "凌傑內建築設計有限公司",
    "TEL:", "E-MAIL:", "ADD:", "浙江省", "云水山庄",
    "厘米", "cm", "A3", "1/65", "63", "號", "中）",
]

# 中文房间名关键词
ROOM_NAME_KEYWORDS = [
    "客厅", "餐厅", "厨房", "卫生间", "卧室", "书房", "影音室",
    "品茶区", "娱乐区", "休闲区", "楼梯厅", "衣帽间", "鞋帽间",
    "储藏间", "设备间", "阳台", "露台", "庭院", "花园", "车库",
    "酒柜", "手工区", "钢琴区", "健身", "过道", "走廊",
    "客卧", "主卧", "次卧", "入户", "门厅",
]

# ============================================================
# 暖通规则表
# ============================================================

# 空调分区规则：房间关键词 → (分区名, 设备类型, 功率, 颜色RGBA)
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

# 地暖分区规则：房间关键词 → (分区名, 管材, 间距, 颜色RGBA)
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
    """判断是否为图框样板文字"""
    for bp in BOILERPLATE:
        if bp in text:
            return True
    return False

def match_room_name(text):
    """从文字中匹配房间名"""
    for kw in ROOM_NAME_KEYWORDS:
        if kw in text:
            return kw
    return None

def match_rule(room_name, rules):
    """用最长匹配法匹配暖通规则"""
    if room_name in rules:
        return rules[room_name]
    # 尝试部分匹配
    best_match = None
    best_len = 0
    for key in rules:
        if key in room_name or room_name in key:
            if len(key) > best_len:
                best_match = rules[key]
                best_len = len(key)
    return best_match

def is_floor_plan_page(texts):
    """判断当前页是否为平面布置图"""
    all_text = " ".join([t["text"] for t in texts])
    for kw in FLOOR_PLAN_KEYWORDS:
        if kw in all_text:
            return True
    return False

def extract_room_names(texts):
    """从PDF文字列表中提取房间名称和位置"""
    rooms = {}
    for t in texts:
        txt = t["text"].strip()
        if is_boilerplate(txt):
            continue
        # 尝试匹配房间名
        room = match_room_name(txt)
        if room and txt not in rooms:
            # 只取中文名（避免英文重复）
            font = t.get("font", "")
            if "SimSun" in font or "SimHei" in font or "SimKai" in font:
                rooms[txt] = {
                    "bbox_pdf": t["bbox"],  # PDF坐标
                    "size": t["size"],
                    "room_type": room,
                }
        # 也检查英文名对应（如果中文名还没收录）
        if not room:
            # 检查是否是英文房间名
            eng_map = {
                "BEDROOM": "卧室", "BATHROOM": "卫生间", "KITCHEN": "厨房",
                "CLOAKROOM": "衣帽间", "STAIRWELL": "楼梯厅", "GARAGE": "车库",
                "GARDEN": "花园", "DRAWINGROOM": "客厅", "PLAY AREA": "娱乐区",
                "MOVEROOM": "影音室", "STORAGE": "储藏间", "BALCONY": "阳台",
                "PATIO": "露台", "PANTRY": "储藏间",
            }
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

def extract_vectors(page):
    """提取PDF矢量路径（墙体线条等）"""
    paths = []
    drawings = page.get_drawings()
    for d in drawings:
        for item in d["items"]:
            if item[0] == "l":  # line
                paths.append(("line", item[1].x, item[1].y, item[2].x, item[2].y))
            elif item[0] == "re":  # rectangle
                r = item[1]
                paths.append(("rect", r.x0, r.y0, r.x1, r.y1))
    return paths

def find_room_boundary(text_center, vectors, page_rect):
    """基于文字中心点 + 矢量路径，推算房间边界
    
    策略：从文字中心向四周扩展，遇到墙体线条则停止。
    如果没找到明确墙体，则用默认扩展比例。
    """
    cx, cy = text_center
    page_w = page_rect.width
    page_h = page_rect.height
    
    # 默认扩展：从中心向四周扩展页面尺寸的一定比例
    # 典型房间占页面面积的5-15%
    margin_x = page_w * 0.12
    margin_y = page_h * 0.15
    
    # 尝试用矢量路径收紧边界
    # 向上搜索（PDF中y增加=向上）
    top = cy + margin_y
    bottom = cy - margin_y
    left = cx - margin_x
    right = cx + margin_x
    
    # 限制在页面范围内
    left = max(left, 30)  # 留出图框
    right = min(right, page_w - 30)
    bottom = max(bottom, 30)
    top = min(top, page_h - 30)
    
    # 在矢量路径中寻找附近的水平/垂直线条来收紧边界
    threshold = 20  # 点(pt)为单位的搜索范围
    
    for vtype, x0, y0, x1, y1 in vectors:
        if vtype == "line":
            # 近似水平线 → 可能是上下墙
            if abs(y0 - y1) < 3 and abs(x0 - x1) > 20:
                if abs(y0 - cy) < margin_y * 1.2:
                    if y0 > cy and y0 < top:
                        top = y0
                    elif y0 < cy and y0 > bottom:
                        bottom = y0
            # 近似垂直线 → 可能是左右墙
            if abs(x0 - x1) < 3 and abs(y0 - y1) > 20:
                if abs(x0 - cx) < margin_x * 1.2:
                    if x0 > cx and x0 < right:
                        right = x0
                    elif x0 < cx and x0 > left:
                        left = x0
    
    return (left, bottom, right, top)

def pdf_to_image_coords(bbox_pdf, page_h, scale):
    """PDF坐标转图片坐标
    PDF: 原点左下, y向上
    图片: 原点左上, y向下
    """
    x0, y0, x1, y1 = bbox_pdf
    ix0 = x0 * scale
    iy0 = (page_h - y1) * scale  # 注意y翻转
    ix1 = x1 * scale
    iy1 = (page_h - y0) * scale
    return (ix0, iy0, ix1, iy1)

# ============================================================
# 绘图函数
# ============================================================

def draw_overlay(base_img, rooms_with_zones, title, legend_items, page_label):
    """在基础图上叠加暖通分区"""
    canvas = base_img.convert("RGBA")
    w, h = canvas.size
    
    font_title = get_font(20)
    font_label = get_font(13)
    font_small = get_font(10)
    font_zone = get_font(11)
    
    # 绘制各分区
    for room_info in rooms_with_zones:
        zone = room_info["zone"]
        boundary = room_info["boundary_img"]  # 图片坐标
        
        # 半透明填充
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rectangle(boundary, fill=zone["color"])
        canvas = Image.alpha_composite(canvas, overlay)
        
        draw = ImageDraw.Draw(canvas)
        # 边框
        draw.rectangle(boundary, outline=zone["color"][:3], width=2)
        
        # 房间名称（白色背景）
        cx = (boundary[0] + boundary[2]) / 2
        cy = (boundary[1] + boundary[3]) / 2
        name = room_info["display_name"]
        bbox = font_label.getbbox(name)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.rectangle([cx - tw/2 - 3, cy - th/2 - 8, cx + tw/2 + 3, cy + th/2 + 8],
                        fill=(255, 255, 255, 220))
        draw.text((cx - tw/2, cy - th/2 - 4), name, fill=(0, 0, 0), font=font_label)
        
        # 设备标注（带彩色背景）
        equip = zone.get("equipment", "")
        load = zone.get("load", "")
        if equip and equip != "-":
            if load and load != "-":
                label = f"{equip} {load}"
            else:
                label = equip
            bbox_e = font_small.getbbox(label)
            ew = bbox_e[2] - bbox_e[0]
            eh = bbox_e[3] - bbox_e[1]
            ex = cx - ew / 2
            ey = cy + th / 2 + 4
            
            # 确保不超出边界
            if ex < boundary[0] + 2:
                ex = boundary[0] + 2
            if ey + eh > boundary[3] - 2:
                ey = boundary[3] - eh - 2
            
            bg = zone["color"][:3] + (200,)
            draw.rectangle([ex - 3, ey - 2, ex + ew + 3, ey + eh + 2], fill=bg)
            draw.text((ex, ey), label, fill=(255, 255, 255), font=font_small)
    
    result = canvas.convert("RGB")
    draw = ImageDraw.Draw(result)
    
    # 标题栏
    draw.rectangle([10, 8, 380, 40], fill=(40, 40, 40))
    full_title = f"{title} - {page_label}"
    draw.text((15, 12), full_title, fill=(255, 255, 255), font=font_title)
    
    # 图例
    lx = w - 280
    ly = 8
    lh = len(legend_items) * 24 + 32
    draw.rectangle([lx, ly, w - 8, ly + lh], fill=(255, 255, 255, 230))
    draw.rectangle([lx, ly, w - 8, ly + lh], outline=(100, 100, 100), width=1)
    draw.text((lx + 8, ly + 6), "图例:", fill=(0, 0, 0), font=font_label)
    
    for i, (name, color, desc) in enumerate(legend_items):
        yy = ly + 28 + i * 24
        draw.rectangle([lx + 8, yy, lx + 24, yy + 16], fill=color + (220,))
        draw.rectangle([lx + 8, yy, lx + 24, yy + 16], outline=(0, 0, 0), width=1)
        draw.text((lx + 28, yy), f"{name}: {desc}", fill=(0, 0, 0), font=font_small)
    
    return result

# ============================================================
# 主流程
# ============================================================
print("=" * 60)
print("暖通示意图自动生成工具")
print("=" * 60)

doc = fitz.open(PDF_PATH)
print(f"PDF: {PDF_PATH}")
print(f"页数: {doc.page_count}")

# 预定义的图例
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
    
    # 4. 提取矢量路径
    vectors = extract_vectors(page)
    print(f"  矢量路径: {len(vectors)} 条")
    
    # 5. 为每个房间推算边界
    room_boundaries = {}
    for name, info in room_names.items():
        bbox = info["bbox_pdf"]
        # 文字中心点（PDF坐标）
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        
        # 推算房间边界（PDF坐标）
        boundary_pdf = find_room_boundary((cx, cy), vectors, rect)
        room_boundaries[name] = {
            "boundary_pdf": boundary_pdf,
            "center_pdf": (cx, cy),
            "room_type": info["room_type"],
        }
    
    # 6. 渲染页面为图片
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
    
    # 7. 生成空调示意图
    ac_rooms = []
    ac_legend_set = set()
    for name, rb in room_boundaries.items():
        rule = match_rule(rb["room_type"], AC_RULES)
        if rule:
            zone_name, equip, load, color = rule
            # 转换为图片坐标
            boundary_img = pdf_to_image_coords(rb["boundary_pdf"], rect.height, SCALE)
            ac_rooms.append({
                "display_name": name,
                "boundary_img": boundary_img,
                "zone": {
                    "name": zone_name,
                    "color": color,
                    "equipment": equip,
                    "load": load,
                }
            })
            if zone_name not in ac_legend_set:
                ac_legend_set.add(zone_name)
    
    if ac_rooms:
        ac_img = draw_overlay(base_img, ac_rooms, "空调系统分区示意图", AC_LEGEND, page_title)
        ac_path = os.path.join(OUT_DIR, f"空调新风示意图_第{page_idx+1}页.png")
        ac_img.save(ac_path, quality=95)
        print(f"  ✅ 空调示意图: {ac_path}")
    
    # 8. 生成地暖示意图
    heat_rooms = []
    for name, rb in room_boundaries.items():
        rule = match_rule(rb["room_type"], HEAT_RULES)
        if rule:
            zone_name, pipe, spacing, color = rule
            boundary_img = pdf_to_image_coords(rb["boundary_pdf"], rect.height, SCALE)
            heat_rooms.append({
                "display_name": name,
                "boundary_img": boundary_img,
                "zone": {
                    "name": zone_name,
                    "color": color,
                    "equipment": pipe,
                    "load": spacing,
                }
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
